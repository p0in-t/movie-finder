import sys
import os
import re
import time
import numpy as np
import datetime
from typing import TypedDict
from functools import partial
from langchain.prompts import PromptTemplate
from langchain.agents import AgentType, initialize_agent, Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from movie_similarity_search import find_similar_movies, find_id_by_title, find_movies_by_id, find_movies_by_description
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get('GEMINI_KEY')

model = ChatGoogleGenerativeAI(
    google_api_key=GEMINI_API_KEY,
    model="gemini-2.5-flash",
    temperature=1.0,
)

class DateTool:    
    def get_current_date(self, _=""):
        return datetime.datetime.now().strftime("%Y-%m-%d")
    
class MovieSearchTool:
    def __init__(self, faiss_index, movie_df, model):
        self.faiss_index = faiss_index
        self.movie_df = movie_df
        self.model = model
    
    def find_by_similarity(self, query_movie_id):
        try:
            query_movie_id = int(query_movie_id)
            result_df, error = find_similar_movies(
                query_movie_id=query_movie_id,
                faiss_index=self.faiss_index,
                movie_df=self.movie_df
            )
            
            if error:
                return f"Error: {error}"
            
            if result_df.empty:
                return "No similar movies found."
            
            output = f"Found {len(result_df)} similar movies to movie ID {query_movie_id}:\n\n"
            for idx, row in result_df.iterrows():
                output += f"{idx+1}. {row['title']} (ID: {row['id']})\n"
                output += f"   Rating: {row['vote_average']}/10\n"
                output += f"   Similarity: {row['similarity_score']:.3f}\n"
                output += f"   Overview: {row['overview'][:100]}...\n\n"
            
            return output.strip()
            
        except ValueError as e:
            return f"Error: Please provide a valid movie ID number. {str(e)}"
        except Exception as e:
            return f"Error occurred: {str(e)}"
        
    def find_by_id(self, query_movie_id):
        try:
            query_movie_id = int(query_movie_id)

            result_df, error = find_movies_by_id(
                query_movie_id=query_movie_id,
                movie_df=self.movie_df
            )

            if error:
                return f"Error: {error}"
            
            if result_df.empty:
                return "No similar movies found."
                        
            output = f"Found movie with movie ID {query_movie_id}:\n\n"

            for idx, row in result_df.iterrows():
                output += f"{idx+1}. {row['title']} (ID: {row['id']})\n"
                output += f"   Rating: {row['vote_average']}/10\n"
                output += f"   Overview: {row['overview'][:100]}...\n\n"

            return output.strip()
            
        except ValueError as e:
            return f"Error: Please provide a valid movie ID number. {str(e)}"
        except Exception as e:
            return f"Error occurred: {str(e)}"
        
    def find_by_description(self, query_description):
        try:
            query_description = str(query_description)
            result_df, error = find_movies_by_description(
                query_description=query_description,
                movie_df=self.movie_df,
                model=self.model
            )
            
            if error:
                return f"Error: {error}"
            
            if result_df.empty:
                return "No similar movies found."
            
            output = f"Found {len(result_df)} movies matching your description:\n\n"
            for idx, row in result_df.iterrows():
                output += f"{idx+1}. {row['title']} (ID: {row['id']})\n"
                output += f"   Rating: {row['vote_average']}/10\n"
                output += f"   Similarity: {row['similarity_score']:.3f}\n"
                output += f"   Overview: {row['overview'][:100]}...\n\n"
            
            return output.strip()
            
        except ValueError as e:
            return f"Error: Please provide a valid movie description. {str(e)}"
        except Exception as e:
            return f"Error occurred: {str(e)}"
        
    def find_id(self, query_title):
        try:
            query_title= str(query_title)
            result, error = find_id_by_title(
                query_title=query_title,
                movie_df=self.movie_df,
            )
            
            if error:
                return f"Error: {error}"
            
            if result is None:
                return "No such movies found."
                        
            return result
            
        except ValueError as e:
            return f"Error: Please provide a valid movie description. {str(e)}"
        except Exception as e:
            return f"Error occurred: {str(e)}"

    
date_tool = DateTool()

class LLMState(TypedDict):
    input: str
    intent: str
    search_intent: str
    verification_result: bool
    requires_human_review: bool
    augmented_query: str
    final_answer: str
    hallucination_check: bool
    messages: list[str]

def hallucination_detection(state):
    print("HALLUCINATION_DETECTION")
    initial_answer = state["final_answer"]
    original_query = state["input"]

    try:
        verification_prompt = PromptTemplate(
            input_variables=["initial_answer", "original_query"],
            template="""You are an expert assistant evaluating an 'Answer' against an 'Original Query'.
            Your task is to determine if the 'Answer' *logically fulfills* the 'Original Query's request for information or interaction, based *only* on the provided text.

            Answer: {initial_answer}
                        
            Original Query: {original_query}
            
            **Evaluation Rules Based on Query Type:**

            1.  **For Temporal/Data Retrieval Queries (e.g., asking for dates, movie information, specific facts):**
                If the 'Original Query' uses relative time expressions (e.g., "now", "last month", "yesterday", "last week"), assume that a **prior, external step has already correctly translated these into specific absolute dates.** Your role is NOT to verify if these absolute dates (e.g., '2025-06-18') genuinely represent 'now' or 'last month' in the real world. Your sole responsibility is to check if the 'Answer' *consistently uses and presents information* that logically corresponds to such a correct date translation. Assume the absolute dates presented in the 'Answer' are the correct interpretation of the relative terms in the 'Original Query'.

            2.  **For All Other Queries (including greetings, social interactions, general questions, or non-data requests):**
                Evaluate if the 'Answer' is a direct, relevant, and appropriate response to the 'Original Query'.
                * An **appropriate response to a greeting** (e.g., "hello", "hi") includes a reciprocal greeting and/or an offer of assistance.
                * An appropriate response to a general question provides a direct and relevant answer.

            Does the 'Answer' provide information or interaction that directly and relevantly addresses the 'Original Query's main request, following the specific rules above for its query type?

            Instructions:
            1.  If the 'Answer' fully and accurately addresses the 'Original Query' (following the specific rules for temporal/data queries OR the general relevance/appropriateness rules for other queries), respond with "YES".
            2.  If the 'Answer' provides irrelevant information, completely misses the point of the 'Original Query', is factually incorrect (for data queries), or inappropriate/nonsensical (for social/general queries), respond with "NO" followed by a brief, specific reason.
            
            Evaluation:"""
        )

        verification_chain = verification_prompt | model 
        result = verification_chain.invoke({"initial_answer": initial_answer, "original_query": original_query})
        expanded_query = result.content if hasattr(result, 'content') else str(result)

        if "YES" in expanded_query.upper().replace(" ", ""):
            return {"hallucination_check": True}
        else:
            return {"hallucination_check": False, "augmented_query": f"Hallucination detection returned: {expanded_query} to users query: {original_query}, your answer was: {initial_answer} "}
    except Exception as e:
        return f"ERROR: An internal error occurred during hallucination detection: {e}"
    
def create_tools(movie_search_tool):
    tools = [
        Tool(
            name="CheckCurrentDate",
            func=date_tool.get_current_date,
            description="Checks today's date. Returns current date in YYYY-MM-DD format."
        ),
        Tool(
            name="FindMoviesBySimilarity",
            func=movie_search_tool.find_by_similarity,
            description="Used to find similar movies to a specific movie. Input should be a movie ID number."
        ),
        Tool(
            name="FindMoviesByID",
            func=movie_search_tool.find_by_id,
            description="Used to find movies by id. Input should be a movie ID number."
        ),
        Tool(
            name="FindMoviesByDescription",
            func=movie_search_tool.find_by_description,
            description="Used to find movies by description. Input should be a string description of a movie."
        ),
        Tool(
            name="FindMovieIDByTitle",
            func=movie_search_tool.find_id,
            description="Used to find IDs of movies by their title. Input should be a string movie title."
        ),
    ]
    return tools

def classify_intent(state):
    query = state["input"]

    classification_prompt = PromptTemplate(
        input_variables=["query"],
        template="""Classify this movie query into ONE category:
        'movie_information_retrieval', 'check_current_date', 'uncertain_query' or 'general_inquiry'.

        'movie_retrieval': Use this if the user wants to get *any* information about movies. This includes finding movies by ID, description and asking for similar movies.
            Examples:
            - "Find me movies like Inception."
            - "Tell me about movie with id 13."
            - "Show me movies that are about breaking out of prison."

        'check_current_date': Use this if the user asks for today's date.
            Example: "What is today's date?"

        'general_inquiry': Use this for anything else that doesn't fit the above categories.
            Example: "What is your purpose?"

        'uncertain_query': Use this if not certain about the users query, if you can not classify as above categories, classify as this.
            Keep in mind that the current query could be in reference to a previous query, so for example "Yes" would not be an uncertain query
            as it is in reference to previous messages.
        
        Query: {query}
        
        Category:"""
    )
    
    classification_chain = classification_prompt | model 
    result = classification_chain.invoke({"query": query})
    expanded_query = result.content if hasattr(result, 'content') else str(result)

    if expanded_query == "uncertain_query":
        return {"intent": expanded_query, "requires_human_input": True}
    else:
        return {"intent": expanded_query, "requires_human_input": False}
    
def classify_search_intent(state):
    query = state["input"]

    classification_prompt = PromptTemplate(
        input_variables=["query"],
        template="""Classify this search query into ONE category:
        'search_via_description', 'search_via_similarity', 'search_via_id'.
        
        Query: {query}
        
        Category:"""
    )
    
    classification_chain = classification_prompt | model 
    result = classification_chain.invoke({"query": query})
    expanded_query = result.content if hasattr(result, 'content') else str(result)
    return {"search_intent": expanded_query}

def create_agent(movie_search_tool):
    return initialize_agent(
        create_tools(movie_search_tool),
        model,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10,
        agent_kwargs={
            "prefix": """You are the Movie Finder, an intelligent and versatile AI assistant with specialized movie search capabilities. 

        **Your Dual Purpose:**
        1. **Primary Expertise:** Accurately answer movie-related questions using your specialized tools
        2. **General Assistant:** Engage in natural conversation on any topic, provide helpful information, advice, or simply chat

        **Conversation Flow Guidelines:**
        - Always check chat history before responding to understand context and avoid repetition
        - Be warm, friendly, and conversational in your tone
        - For movie queries, use your tools precisely as described below
        - For non-movie topics, draw on your knowledge and reasoning abilities
        - Seamlessly transition between movie assistance and general conversation as needed

        ---
        **MOVIE TOOL USAGE GUIDE**

        When handling movie-related requests, follow these principles:

        **Core Tool Principles:**
        1. **Tool-Based Knowledge Only:** For movie information, rely EXCLUSIVELY on tool observations. Never use internal movie knowledge.
        2. **Stop on Success:** Once tools provide complete information that answers the user's request, immediately give your Final Answer.
        3. **Sequential Logic:** Some queries require multiple tool calls in sequence - plan your approach carefully.

        **Available Tools:**

        **1. `FindMovieIDByTitle`**
        - **Purpose:** Convert movie title to unique numerical ID (required for similarity searches)
        - **Input:** Exact movie title as string
        - **When to use:** Always use FIRST when user wants movies "like" or "similar to" a named movie
        - **Example:**
        ```
        Action: FindMovieIDByTitle
        Action Input: Inception
        ```

        **2. `FindMoviesBySimilarity`**
        - **Purpose:** Find movies similar to a specific movie
        - **Critical:** Requires movie ID number (not title) as input
        - **Input:** Single integer movie ID
        - **When to use:** After getting ID from `FindMovieIDByTitle`
        - **Example:**
        ```
        Action: FindMoviesBySimilarity
        Action Input: 27205
        ```

        **3. `FindMoviesByDescription`**
        - **Purpose:** Search movies by plot, theme, genre, or concept
        - **Input:** Descriptive string about movie content
        - **When to use:** User describes what they want without naming a specific movie
        - **Example:**
        ```
        Action: FindMoviesByDescription
        Action Input: psychological thriller about memory loss and identity
        ```

        **4. `FindMoviesByID`**
        - **Purpose:** Get detailed information about a specific movie
        - **Input:** Single integer movie ID
        - **When to use:** User provides a movie ID or you need details about a specific movie
        - **Example:**
        ```
        Action: FindMoviesByID
        Action Input: 155
        ```

        **5. `CheckCurrentDate`**
        - **Purpose:** Get today's real-world date
        - **Input:** Empty string
        - **When to use:** Only when user explicitly asks for current date
        - **Example:**
        ```
        Action: CheckCurrentDate
        Action Input: ""
        ```

        ---
        **STRATEGIC WORKFLOWS**

        **Workflow 1: "Movies Like [Title]" Requests**
        This ALWAYS requires two steps:

        1. **Get Movie ID:**
        - User mentions a movie title they want recommendations based on
        - Think: "I need the ID for this movie first"
        - Use `FindMovieIDByTitle` with the exact title

        2. **Find Similar Movies:**
        - Use the ID from step 1 as input for `FindMoviesBySimilarity`
        - Present results in your Final Answer

        **Example thought process:**
        ```
        User: "Find movies like Blade Runner"
        Thought: User wants similar movies to "Blade Runner". I need the movie ID first.
        Action: FindMovieIDByTitle
        Action Input: Blade Runner
        Observation: [ID retrieved]
        Thought: Now I have the ID. I can find similar movies.
        Action: FindMoviesBySimilarity  
        Action Input: [retrieved ID]
        Observation: [Similar movies list]
        Final Answer: [Present the similar movies in a friendly, readable format]
        ```

        **Workflow 2: Description-Based Searches**
        Single step process:
        - User describes movie concept, plot, or theme
        - Use `FindMoviesByDescription` directly
        - Present results in Final Answer

        **Workflow 3: Specific Movie Information**
        Single step process:
        - User provides movie ID or asks about a specific movie you already have the ID for
        - Use `FindMoviesByID`
        - Present information in Final Answer

        **Workflow 4: General Conversation**
        - No tools needed for non-movie topics
        - Engage naturally using your knowledge and reasoning
        - Be helpful, informative, and conversational
        - Transition smoothly back to movie assistance if the topic shifts

        ---
        **RESPONSE QUALITY GUIDELINES**

        - **Be Conversational:** Write in a natural, friendly tone
        - **Be Precise:** When using tools, follow the exact input formats
        - **Be Complete:** Provide comprehensive answers that fully address the user's request
        - **Be Contextual:** Reference previous parts of the conversation when relevant
        - **Be Helpful:** Offer additional relevant information or suggestions when appropriate

        **Error Handling:**
        - If tools don't provide the needed information, clearly explain this limitation
        - Suggest alternative approaches when possible
        - For general topics, acknowledge if you're uncertain about something

        ---
        ---
        **CRITICAL: RESPONSE FORMAT**

        You MUST always follow this exact format for every response:

        **For responses that require tools:**
        ```
        Thought: [Your reasoning about what you need to do]
        Action: [Tool name]
        Action Input: [Tool input]
        Observation: [Tool output - this will be provided automatically]
        Thought: [Your reasoning about the observation]
        Final Answer: [Your response to the user]
        ```

        **For responses that DON'T require tools (greetings, general chat, non-movie topics):**
        ```
        Thought: [Brief reasoning about the user's message]
        Final Answer: [Your direct response to the user]
        ```

        **NEVER:**
        - Skip the "Thought:" step
        - Go directly to "Final Answer:" without a "Thought:" first
        - Use tools for simple greetings or general conversation
        - Provide responses outside this format

        **Examples:**

        *User: "Hello!"*
        ```
        Thought: The user is greeting me. This is a simple social interaction that doesn't require any movie tools.
        Final Answer: Hello there! It's great to meet you. How can I help you today? Are you looking for a movie recommendation, or perhaps just want to chat? I'm here for whatever you need!
        ```

        *User: "How are you?"*
        ```
        Thought: The user is asking about my well-being. This is casual conversation that doesn't require tools.
        Final Answer: I'm doing well, thank you for asking! I'm here and ready to help with whatever you need - whether that's finding the perfect movie to watch or just having a friendly chat. What's on your mind today?
        ```

        *User: "Find movies like The Matrix"*
        ```
        Thought: The user wants movies similar to "The Matrix". I need to first get the movie ID for "The Matrix" using FindMovieIDByTitle, then use that ID with FindMoviesBySimilarity.
        Action: FindMovieIDByTitle
        Action Input: The Matrix
        ```

        ---
        **Remember:** Every single response must start with "Thought:" and end with "Final Answer:" - no exceptions!

        **Past Conversation History:**
        {chat_history}

        Begin!
        """
        }
    )

def parse_input(user_input):
    if user_input.lower() in ['quit', 'exit', 'q']:
        return None
        
    return user_input

def human_input(state):
    print("HUMAN INPUT")
    user_input = state['input']

    messages = state["messages"]
    max_messages = 10

    if len(messages) > max_messages:
        messages = messages[-max_messages:]
    
    return {"augmented_query": user_input, "messages": messages}

def movie_retrieval_id(state):
    augmented_query = f"I need to find a specific movie with the ID from the following query: {state['input']}"
    return {"augmented_query": augmented_query}

def movie_retrieval_description(state):
    augmented_query = f"I need to find all movies that match the following description: {state['augmented_query']}"
    return {"augmented_query": augmented_query}

def movie_retrieval_similarity(state):
    augmented_query = f"I need to find all movies that are similar to the specific movie in this query: {state['input']}"
    return {"augmented_query": augmented_query}

def check_current_date(state):
    augmented_query = "What is today's date?"
    return {"augmented_query": augmented_query}

def general_inquiry(state):
    print("GENERAL")
    return {"augmented_query": state["input"]}

def get_response(state, agent):
    print("GET RESPONSE")
    augmented_query = state["augmented_query"]
    messages = state["messages"]

    chat_history = "\n---\n".join(messages)

    try:
        result = agent.invoke({"input":augmented_query, "chat_history":chat_history})
        return {"final_answer": result}
    except Exception as agent_error:
        print(f"Agent error: {agent_error}")

def final_answer(state):
    print("FINAL_ANSWER")
    intent = state["intent"]
    final_answer = state["final_answer"]["output"] if intent != "uncertain_query" else "I can not help you with that, please try again!"
    return {"final_answer": final_answer}

def route_after_classification(state):
    intent = state["intent"]

    if intent == 'movie_information_retrieval':
        return 'classify_search'
    elif intent == 'check_current_date':
        return 'check_current_date'
    elif intent == 'uncertain_query':
        return 'final_answer'
    else:
        return 'general_inquiry'
    
def route_search_intent(state):
    intent = state["search_intent"]

    if intent == 'search_via_id':
        return 'movie_retrieval_id'
    elif intent == 'search_via_similarity':
        return 'movie_retrieval_similarity'
    else:
        return 'movie_retrieval_description'
    
def route_hallucination_detection(state):
    if state["hallucination_check"] == True:
        return "final_answer"
    else:
        return 'get_response'
    
def get_graph(agent):
    input_n = RunnableLambda(human_input)
    classification_n = RunnableLambda(classify_intent)
    classification_search_n = RunnableLambda(classify_search_intent)
    general_inquiry_n = RunnableLambda(general_inquiry)
    check_current_date_n = RunnableLambda(check_current_date)
    movie_retrieval_similarity_n = RunnableLambda(movie_retrieval_similarity)
    movie_retrieval_description_n = RunnableLambda(movie_retrieval_description)
    movie_retrieval_id_n = RunnableLambda(movie_retrieval_id)

    response_partial = partial(get_response, agent=agent) 
    get_response_n = RunnableLambda(response_partial)
    hallucination_detection_n = RunnableLambda(hallucination_detection)
    final_answer_n = RunnableLambda(final_answer)

    builder = StateGraph(LLMState)

    builder.add_node("input", input_n)
    builder.add_node("classification", classification_n)
    builder.add_node("classify_search", classification_search_n)
    builder.add_node("check_current_date", check_current_date_n)
    builder.add_node("movie_retrieval_id", movie_retrieval_id_n)
    builder.add_node("movie_retrieval_description", movie_retrieval_description_n)
    builder.add_node("movie_retrieval_similarity", movie_retrieval_similarity_n)
    builder.add_node("general_inquiry", general_inquiry_n)
    builder.add_node("get_response", get_response_n)

    builder.add_node("hallucination_detection", hallucination_detection_n)
    builder.add_node("final_answer", final_answer_n)
    # builder.add_node("human_in_loop", human_in_loop_n)

    builder.set_entry_point("input")

    builder.add_edge("input", "classification")

    builder.add_conditional_edges(
        "classification",
        route_after_classification,
        {
            "classify_search": "classify_search",
            "check_current_date": "check_current_date",
            "general_inquiry": "general_inquiry",
            "final_answer": "final_answer"
        }
    )

    builder.add_conditional_edges(
        "classify_search",
        route_search_intent,
        {
            "movie_retrieval_id": "movie_retrieval_id",
            "movie_retrieval_description": "movie_retrieval_description",
            "movie_retrieval_similarity": "movie_retrieval_similarity"
        }
    )

    builder.add_conditional_edges(
        "hallucination_detection",
        route_hallucination_detection,
        {
            "get_response": "get_response",
            "final_answer": "final_answer"
        }
    )

    for node in ["check_current_date", "movie_retrieval_similarity",
                  "movie_retrieval_id", "movie_retrieval_description",
                  "general_inquiry"]:
        builder.add_edge(node, "get_response")

    builder.add_edge("get_response", "hallucination_detection")
    builder.add_edge("final_answer",  END)

    # builder.add_edge("human_in_loop", "input")

    graph = builder.compile()

    return graph

def init_llm(movie_search_tool):
    agent = create_agent(movie_search_tool)
    graph = get_graph(agent)

    return agent, graph

# def run_llm(user_input):
#     print("Loading index and movie dataframe...")
#     movie_df, faiss_index = load_or_build_index(conn, cursor)
#     print("Loading model...")
#     sbert_model = SentenceTransformer('paraphrase-MiniLM-L3-v2', device='cpu')
#     print("Initializing movie search tool...")
#     movie_search_tool = MovieSearchTool(faiss_index=faiss_index, movie_df=movie_df, model=sbert_model)

#     agent, graph = init_llm(movie_search_tool)
    
#     try:
#         response = graph.invoke({"input":user_input}, {"recursion_limit":50})

#         return response
#     except KeyboardInterrupt:
#         sys.exit()
#     except Exception as e:
#         print(f"\nAn error occurred: {e}\nPlease try again.\n")

# run_llm('hello')