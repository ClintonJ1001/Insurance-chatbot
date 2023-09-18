import streamlit as st
from streamlit_chat import message

import pandas as pd

from database import get_redis_connection, get_redis_results
from chatbot import RetrievalAssistant, Message

from prompts import system_prompt_QE, system_prompt_C, system_prompt_CS1, system_prompt_CS2, system_prompt_IA, system_prompt_EA, user_prompt_EA

from config import PDS_INDEX_NAME, CONTRACT_INDEX_NAME

# Initialise database

## Initialise Redis connection
redis_client = get_redis_connection()

### CHATBOT APP

st.set_page_config(
    page_title="Helpful Insurance AI",
    page_icon=":robot:"
)

st.title('Insurance Chatbot')
st.subheader("Ask me anything about your product or contract")

if 'generated' not in st.session_state:
    st.session_state['generated'] = []

if 'past' not in st.session_state:
    st.session_state['past'] = []

##used in debugging
def display_messages(to_print):
    for each_message in to_print:
        st.write(f"{each_message.role}: {each_message.content}")

prompt = st.text_input(f"What do you want to know: ", key="input")

if st.button('Submit', key='generationSubmit'):

    # Initialization
    if 'chat' not in st.session_state:
        st.session_state['chat'] = RetrievalAssistant()
        messages = []
    else:
        messages = []

## Run the Query Expert to create the text to search for in the reference documents
    #Query parameters
    system_message = Message('system',system_prompt_QE)
    user_message = Message('user',prompt)
    messages.append(system_message.message())
    messages.append(user_message.message())
    temp = 1.5
    length = 256
    resp_count = 3
    
    #generate 3 responses with high temp to cast a wide net for search terms, 
    responses = st.session_state['chat']._get_assistant_response(messages, temp, length, resp_count)

    # Testing QE output
    # display_messages(responses)

# Combine the results and if an insurance question proceed with runing 
# the consolidator to provide a combined set of terms removing any duplicates

    # Initialize an empty string to store the combined terms
    combined_terms = ""
    
    # Loop through the responses and concatenate their content
    for each_response in responses:
        combined_terms += each_response.content
    
    # Don't proceed if its not an insurance question
    if "NOT INSURANCE" not in combined_terms:
    
        #Query parameters
        messages = []
        system_message = Message('system',system_prompt_C)
        user_message = Message('user',combined_terms)
        messages.append(system_message.message())
        messages.append(user_message.message())
        temp = 0.5
        length = 256
        resp_count = 1
    
        #Generate response lower temp
        consolidated_response = st.session_state['chat']._get_assistant_response(messages, temp, length, resp_count)
        
        #Display for debugging
        #display_messages(consolidated_response)
    
        search_terms = ""
        for each_consolidated_response in consolidated_response:
            search_terms += each_consolidated_response.content


        # Run the Redis search on the combined terms within the PDS index
        PDS_content = get_redis_results(
                redis_client,search_terms, 
                PDS_INDEX_NAME
            )
        
        # Run the Redis search on the combined terms within the Contract index
        Contract_content = get_redis_results(
                redis_client,search_terms, 
                CONTRACT_INDEX_NAME
            )

        #Combine them
        search_content = pd.concat([PDS_content, Contract_content], ignore_index=True)

        # For debugging
        #st.write(search_content)

        # Convert the search results into a long string
        results_string = ' '.join(search_content['result'].astype(str))
                
        # Summarise the content returned from Redis

        #Query parameters
        messages = []
        system_message = Message('system',system_prompt_CS1 + ' ' + results_string + ' ' + system_prompt_CS2)
        user_message = Message('user',prompt)
        messages.append(system_message.message())
        messages.append(user_message.message())
        temp = 1.5
        length = 256
        resp_count = 1
        

        #generate 3 responses with average temp to help ensure the best points are extracted without going to random
        responses = st.session_state['chat']._get_assistant_response(messages, temp, length, resp_count)

        # Testing content summarisation output
        # display_messages(responses)
    
        # Initialize an empty string to store the combined terms
        combined_summarisation = ""
        
        # Loop through the responses and concatenate their content
        for each_response in responses:
            combined_summarisation += each_response.content

        # Generate 3 possible answers to the customer based on the information that has been summarised.

        #Query parameters
        messages = []
        system_message = Message('system', (system_prompt_IA + ' ' + combined_summarisation))
        user_message = Message('user',prompt)
        messages.append(system_message.message())
        messages.append(user_message.message())
        temp = 1.5
        length = 256
        resp_count = 3

        # Generate 3 responses with a.verage temp to later filter out any incorrect responses
        # Used higher temperature to generate a wider range of answers for this step
        responses = st.session_state['chat']._get_assistant_response(messages, temp, length, resp_count)
    
        # Testing content summarisation output
        #display_messages(responses)
    
        # Loop through the responses and concatenate their content
        combined_answers = ""
        counter = 1
        
        for each_response in responses:
            combined_answers += f'Response {counter}: {each_response.content}\n'
            counter += 1

        # Finally generate feedback on the three answers and use that feedback to determine the best response
        
        #Query parameters
        messages = []
        user_message = Message('user',combined_answers)
        system_message = Message('system', (system_prompt_EA + 'CUSTOMER QUESTION: ' + prompt 
                                + 'RELEVANT CONTENT: ' + combined_summarisation + 'SUGGESTED RESPONSES: ' 
                                + combined_answers))
        messages.append(system_message.message())
        messages.append(user_message.message())
        temp = 1
        length = 512
        resp_count = 1

        # Generate feedback on the responses first
        responses = st.session_state['chat']._get_assistant_response(messages, temp, length, resp_count)

        # Testing feedback output
        #display_messages(responses)

        feedback = ''
                 
        for each_response in responses:
            feedback += each_response.content

        # Generate final answer to provide to customer
        user_message = Message('user',user_prompt_EA)
        assistant_message = Message('assistant',feedback)
        messages.append(assistant_message.message())
        messages.append(user_message.message())
        temp = 1
        length = 512
        resp_count = 1
       
        # Generate final response
        responses = st.session_state['chat']._get_assistant_response(messages, temp, length, resp_count)
                 
        # Testing feedback output
        #display_messages(responses)

        final_response = responses[0].content

    else: final_response = 'My apologies I can only answer insurance questions. Please ask something else.' 
        
    # Update the displayed conversation
    st.session_state.past.append(prompt)
    st.session_state.generated.append(final_response)

    
if st.session_state['generated']:

    for i in range(len(st.session_state['generated'])-1, -1, -1):
        message(st.session_state["generated"][i], key=str(i))
        message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')
