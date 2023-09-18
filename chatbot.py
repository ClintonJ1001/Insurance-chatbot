import openai
from termcolor import colored
import streamlit as st

from database import get_redis_connection, get_redis_results

from config import CHAT_MODEL, COMPLETIONS_MODEL, PDS_INDEX_NAME, CONTRACT_INDEX_NAME

from apikey import API_KEY

openai.api_key = API_KEY

redis_client = get_redis_connection()

# A basic class to create a message as a dict for chat
class Message:
    
    def __init__(self, role,content):
        self.role = role
        self.content = content
        
    def message(self):
        return {
            "role": self.role,
            "content": self.content
        }


# New Assistant class to add a vector database call to its responses
class RetrievalAssistant:
    
    def __init__(self):
        self.conversation_history = []  

    def _get_assistant_response(self, prompt, temp, length, responses):

        response_messages = []
        
        try:
            completion = openai.ChatCompletion.create(
              model=CHAT_MODEL,
              messages=prompt,
              n = responses,
              max_tokens = length,
              temperature=temp
            )
            for i in range(responses):
                response_messages.append(Message(
                    completion['choices'][i]['message']['role'],
                    completion['choices'][i]['message']['content']
                ))

            return response_messages
            
        except Exception as e:

            return f'Request failed with exception {e}'
    
    # The function to retrieve Redis search results

    def _get_search_results(self,prompt):
        latest_question = prompt
        search_content = get_redis_results(
            redis_client,latest_question, 
            INDEX_NAME
        )['result'][0]

        return search_content
        
    
    def pretty_print_conversation_history(
            self, 
            colorize_assistant_replies=True):
        
        for entry in self.conversation_history:
            if entry['role']=='system':
                pass
            else:
                prefix = entry['role']
                content = entry['content']
                if colorize_assistant_replies and entry['role'] == 'assistant':
                    output = colored(f"{prefix}:\n{content}, green")
                else:
                    output = colored(f"{prefix}:\n{content}")
                print(output)
