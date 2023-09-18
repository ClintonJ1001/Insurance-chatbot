# Example of using ChatGPT to power an insurance chatbot

The starting point for this work is the openai cookbok chatbot kick-starter

This repo contains one notebook and a basic Streamlit apps:
- `Insurance Chatbot.ipynb`: A notebook containing a step by step process of tokenising, chunking and embedding the data in a vector database. 
- `chat.py`: A Streamlit app providing a simple Chatbot via a search bar to query the knowledge base.

My goal was to experiment with having multiple data stores. While its not necessary in this example I can see situations where this woudl be useful in a real business context.

Also given the stochastic nature of the model, I wanted to try generating mutiple responses at various steps and then using a new interaction with the model to evaluate and determine the best answers. 

Given the approach I experiemented with using a higher temperature for the initial response generations to get a braoder range of possiblilities. These were then filtered and consolidated by a lower temperature interaction to evaluate and combine them.

## How it works

You must start with the notebook as it loads the data into the vector database which is the knowledge base for the chat app
It is laid out in these sections:
- **Setup:** 
    - Initiate variables and source the data
- **Lay the foundations:**
    - Set up the vector database to accept vectors and data
    - Load the dataset, chunk the data up for embedding and store in the vector database

- **The chat application:**
    - The update from the original involves using ChatGPT to come up with improved search terms for the database
    - Creates multiple responses to the questions which are then evaluated within another conversation
    - surfaces up the final answer
 
## Limitations

This is still very much a work in progress. Its not great at surfacing information from the contract. I think this is mainly due to the poor quality of the contract PDF conversion. I am going to try cleaning this document up a bit as I'm sure that will dramatically improve it.

Its quite slow. No doubt this largely due to the mutiple calls on the model. While its too slow for a practical application as is, the quality of the responses is dramatically improved by this process. If you uncomment out code that writes every interaction to the user you can see how the model goes on a tangent sometimes but the evaluation / consolidation steps really takes care of this behaviour.

This approach could be extended to evaluate the interaction against applicable laws or regulations, other internal documents or style guides.
