import pandas as pd 
import numpy as np
import openai
import redis
from redis import Redis
from redis.commands.search.field import VectorField, TextField, NumericField
from redis.commands.search.query import Query
# Added
from redis.commands.search.indexDefinition import IndexDefinition

from config import EMBEDDINGS_MODEL, VECTOR_FIELD_NAME

# Get a Redis connection
def get_redis_connection(host='localhost',port='6379',db=0):
    
    r = Redis(host=host, port=port, db=db,decode_responses=False)
    return r

# Create a Redis index to hold our data
def create_hnsw_index (redis_conn,vector_field_name,vector_dimensions=1536, distance_metric='COSINE'):
    redis_conn.ft().create_index([
        VectorField(vector_field_name, "HNSW", {"TYPE": "FLOAT32", "DIM": vector_dimensions, "DISTANCE_METRIC": distance_metric}),
        TextField("filename"),
        TextField("text_chunk"),        
        NumericField("file_chunk_index")
    ])

# Create a Redis pipeline to load all the vectors and their metadata
def load_vectors(client: Redis, input_list, vector_field_name, index_name, prefix):
    p = client.pipeline(transaction=False)
    index = client.ft(index_name)  # Get the RediSearch index instance
    print(f'load_vector started with vector: {vector_field_name} and index: {index_name} and input list size: {len(input_list)}')
    for text in input_list:
        #hash key
        key = f"{prefix}:{text['id']}"
        
        #hash values
        item_metadata = text['metadata']
        
        item_keywords_vector = np.array(text['vector'], dtype='float32').tobytes()
        item_metadata[vector_field_name] = item_keywords_vector

        # Use RediSearch's add_document method to insert data into the index, delete if it exists already
        # Delete the existing document if it exists
        try:
            index.delete_document(key)
            #print(f"Deleted existing document for key: {key}")
        except redis.exceptions.ResponseError as e:
            if "Document not found" not in str(e):
                # Handle other Redis-related errors
                print(f"Error deleting document from Redis: {e}")
    
        # Add the new document
        try:
            index.add_document(key, **item_metadata)
            #print(f'Added key:{key} to index:{index_name} in pipeline successfully')
        except redis.exceptions.ResponseError as e:
            # Handle any errors that may occur when adding the new document
            print(f"Error adding document to pipeline: {e}")

    try:
        p.execute()  # Execute the Redis pipeline
        print(f"Pipeline executed")
    except Exception as e:
        print(f"Error executing Redis pipeline: {e}")
    


# Make query to Redis
def query_redis(redis_conn,query,index_name, top_k=2):
    
    

    ## Creates embedding vector from user query
    embedded_query = np.array(openai.Embedding.create(
                                                input=query,
                                                model=EMBEDDINGS_MODEL,
                                            )["data"][0]['embedding'], dtype=np.float32).tobytes()

    #prepare the query
    q = Query(f'*=>[KNN {top_k} @{VECTOR_FIELD_NAME} $vec_param AS vector_score]').sort_by('vector_score').paging(0,top_k).return_fields('vector_score','filename','text_chunk','text_chunk_index').dialect(2) 
    params_dict = {"vec_param": embedded_query}

    
    #Execute the query
    results = redis_conn.ft(index_name).search(q, query_params = params_dict)
    
    return results

# Get mapped documents from Weaviate results
def get_redis_results(redis_conn,query,index_name):
    
    # Get most relevant documents from Redis
    query_result = query_redis(redis_conn,query,index_name)
    
    # Extract info into a list
    query_result_list = []
    for i, result in enumerate(query_result.docs):
        result_order = i
        text = result.text_chunk
        score = result.vector_score
        query_result_list.append((result_order,text,score))
        
    # Display result as a DataFrame for ease of us
    result_df = pd.DataFrame(query_result_list)
    result_df.columns = ['id','result','certainty']
    return result_df