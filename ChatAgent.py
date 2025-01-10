import os
from openai import OpenAI
import asyncio
import tiktoken
import pickle
from datetime import datetime, timezone
from semantic_sql import semantic_sql_db





def current_utc_timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def save_ChatAgent_as_txt(agent,filename):
    """
    Saves an instantiatable body of text representing the current chat agent
    and all of it's conversational data
    """
    if ".txt" not in filename:
        filename = filename+".txt"
    with open(filename, 'w') as myfile: 
        content = repr(agent)
        myfile.write(content)

def load_ChatAgent_from_txt(filename):
    """
    Instantiates a chat agent from a saved txt file
    """
    repr_str=None
    with open(filename, 'r') as myfile: 
        repr_str = myfile.read()
    new_instance = eval(repr_str)
    return new_instance


def save_ChatAgent_as_pickle(agent, filename):
    """
    Save a ChatAgent instance to a pickle file, excluding non-pickleable objects like the OpenAI client.
    """
    temp_client = agent.client  # Temporarily store the OpenAI client
    agent.client = None  # Remove the client before pickling
    if ".pickle" not in filename:
        filename = filename + ".pickle"
    with open(filename, 'wb') as file:
        pickle.dump(agent, file)
    agent.client = temp_client  # Restore the client after pickling


def load_ChatAgent_from_pickle(filename, api_key):
    """
    Load a ChatAgent instance from a pickle file and reinitialize non-pickleable objects like the OpenAI client.
    """
    with open(filename, 'rb') as file:
        agent = pickle.load(file)
    # Reinitialize the OpenAI client if the API key is available
    agent.client = OpenAI(api_key=api_key)
    return agent











class ChatAgent:
    def __init__(self, name, api_key=None, model="gpt-3.5-turbo", messages=None, token_limit=4096, summary_size=None):
        self.name = name
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.messages = messages if messages is not None else []
        self.token_limit = token_limit
        self.enc = tiktoken.encoding_for_model(self.model)
        self.primary_directive = None
        self.summary_size = summary_size

        self.conversation_sql_db = self.name+"_conversations/sql_db"
        self.conversation_semantic_db = self.name+"_conversations/semantic_db"
        self.conversation_memory = semantic_sql_db(sql_db_path = self.conversation_sql_db, semantic_db_dir = self.conversation_semantic_db)
        self.conversation_table_schema = {
            "id": "TEXT PRIMARY KEY", # unique id field
            "conversation": "TEXT NOT NULL", # semantic search field
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP"
        }
        self.conversation_memory.set_table(
            table_name="conversations",
            semantic_search_field="conversation",  # This field will be queried semantically
            unique_id_field="id", # this field will be the unique identifier
            table_sql_schema=self.conversation_table_schema
        )

        self.documents_sql_db = self.name+"_documents/sql_db"
        self.documents_semantic_db = self.name+"_documents/semantic_db"
        self.documents_memory = semantic_sql_db(sql_db_path = self.documents_sql_db, semantic_db_dir = self.documents_semantic_db)
        self.documents_table_schema = {
            "id": "TEXT PRIMARY KEY", # unique id field
            "text": "TEXT NOT NULL", # semantic search field
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            "doc_name": "TEXT",
            "chunk": "INTEGER"
        }
        self.documents_memory.set_table(
            table_name="documents",
            semantic_search_field="text",  # This field will be queried semantically
            unique_id_field="id", # this field will be the unique identifier
            table_sql_schema=self.documents_table_schema
        )


    def set_primary_directive(self, system_prompt=None):
        if system_prompt is None and self.primary_directive is not None:
            system_prompt = self.primary_directive
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})
            self.primary_directive = system_prompt

    def count_tokens(self):
        num_tokens = 0
        for message in self.messages:
            num_tokens += len(self.enc.encode(message["content"]))
        return num_tokens

    def is_within_token_limit(self, token_limit=None):
        if token_limit is None:
            token_limit = self.token_limit
        current_token_count = self.count_tokens()
        return current_token_count <= token_limit

    def tokens_left(self):
        t = self.count_tokens()
        return int(self.token_limit) - int(t)

    def extract_messages_content(self):
        return ' '.join(entry['content'] for entry in self.messages if 'content' in entry)

    def words_in_messages(self):
        return len(self.extract_messages_content().split(" "))

    def add_context(self, system_prompt=None):
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def refresh_session(self):
        if self.summary_size is None:
            summary = self.summarize_current_conversation(self.words_in_messages//2)
        else:
            summary = self.summarize_current_conversation()
        self.save_current_conversation_to_memory()
        self.messages = []
        self.set_primary_directive()
        self.add_context("The following has been previously discussed ... " + str(summary))


    def send_message(self, user_message):
        tokens_used_user = len(self.enc.encode(user_message))
        current_token_count = self.count_tokens()
        print("CURRENT TOKENS USED: " + str(current_token_count))
        print("MAX TOKENS: " + str(self.token_limit))
        if current_token_count + tokens_used_user > self.token_limit:
            print("ABOUT TO GO OVER TOKEN LIMIT")
            self.refresh_session()
            print("CONVERSATION WAS REFRESHED")

        # Add user message to conversation history
        self.messages.append({"role": "user", "content": user_message})
        response = self.client.chat.completions.create(model=self.model,
                                                       messages=self.messages)
        ai_message = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": ai_message})
        return ai_message

    async def send_message_async(self, user_message):
        # Use asyncio.to_thread to run the synchronous side_message method asynchronously
        response = await asyncio.to_thread(lambda: self.send_message(user_message))
        return response  # side_message already returns the content

    def get_conversation_history(self):
        # Returns the entire conversation history
        return self.messages


    def side_message(self, prompt, use_context = False):
        # get side message that will not affect overall conversation or be added to conversation history
        temp_messages = []
        if use_context:
            temp_messages = self.messages.copy()
        temp_messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(model=self.model,
                                                       messages=temp_messages)
        return response.choices[0].message.content


    async def side_message_async(self, prompt, use_context=False):
        # Use asyncio.to_thread to run the synchronous side_message method asynchronously
        response = await asyncio.to_thread(lambda: self.side_message(prompt, use_context))
        return response  # side_message already returns the content


    def summarize_current_conversation(self,in_max_n_words=None):
        if in_max_n_words is None:
            in_max_n_words = self.summary_size
        q = """
        Summarize the entire conversation we have had in in_max_n_words
        words or less. Make a note of key information you learned about 
        the user and what key recomendations you gave to the user or 
        key information you shared with the user.
        """
        q = q.replace("in_max_n_words",str(in_max_n_words))
        return self.side_message(q, use_context=True)


    def __repr__(self):
        repr_str = (
            f"ChatAgent(api_key='{self.api_key}', "
            f"model='{self.model}', "
            f"token_limit={self.token_limit}, "
            f"messages={repr(self.messages)}, "
            f"summary_size={repr(self.summary_size)})"
        )
        return repr_str

    def repr_no_key(self):
        repr_str = (
            f"ChatAgent(api_key=None, "
            f"model='{self.model}', "
            f"token_limit={self.token_limit}, "
            f"messages={repr(self.messages)}, "
            f"summary_size={repr(self.summary_size)})"
        )
        return repr_str

    def save_as_txt(self, filename):
        if ".txt" not in filename:
            filename = filename+".txt"
        with open(filename, 'w') as myfile: 
            content = repr(self)
            myfile.write(content)

    def load_from_txt(self, filename):
        repr_str=None
        with open(filename, 'r') as myfile: 
            repr_str = myfile.read()
        new_instance = eval(repr_str)
        attributes = [
            attr
            for attr in dir(new_instance)
            if not callable(getattr(new_instance, attr)) and not attr.startswith("__")
        ]
        for attr in attributes:
            setattr(self, attr, getattr(new_instance, attr))

    def save_as_pickle(self, filename):
        temp_client = self.client  # Temporarily store the OpenAI client
        self.client = None  # Remove the client before pickling
        if ".pickle" not in filename:
            filename = filename + ".pickle"
        with open(filename, 'wb') as file:
            pickle.dump(self, file)
        self.client = temp_client  # Restore the client after pickling

    def load_from_pickle(self, filename):
        with open(filename, 'rb') as file:
            loaded_instance = pickle.load(file)
        # Update current instance's attributes (excluding special methods)
        attributes = [
            attr
            for attr in dir(loaded_instance)
            if not callable(getattr(loaded_instance, attr)) and not attr.startswith("__")
        ]
        for attr in attributes:
            setattr(self, attr, getattr(loaded_instance, attr))
        # Reinitialize the OpenAI client
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)


    def split_messages_into_pairs(self, messages=None):
        """
        returns A list of list of dicts where each list contains [system_entry, user_entry, assistant_entry]
        system_entry is only present when one was found before the user_entry, assistant_entry pair.
        """
        if messages is None:
            messages = self.messages
        pairs = []
        temp_user_entry = None
        temp_system_entry = None
        for entry in messages:
            if entry['role'] == 'system':
                temp_system_entry = entry
            elif entry['role'] == 'user':
                temp_user_entry = entry
            elif entry['role'] == 'assistant' and temp_user_entry:
                # Include system entry only for the closest pair
                pairs.append([temp_system_entry, temp_user_entry, entry])
                temp_user_entry = None
                temp_system_entry = None  # Reset system entry after it's paired
        return pairs

    def save_current_conversation_to_memory(self):
        pairs = self.split_messages_into_pairs()
        data = []
        current_time = current_utc_timestamp()
        for p in pairs:
            d = {"conversation":repr(p), "created_at":current_time}
            data.append(d)
        return self.conversation_memory.insert(data)


    def fetch_relevent_info_from_prior_conversation(query_text,top_k=3, sql_where=None):
        data = self.conversation_memory.hybrid_query(query_text, top_k=top_k, sql_where=sql_where)
        self.add_context("The following was discussed in an earlier conversation and may be relevent ... "+repr(data))


    def ingest_document_text(self, text, metadata=None, max_sentences_per_chunk=10, check_validity=False):
        return self.documents_memeory.insert_text_in_chunks(text, metadata=metadata, max_sentences_per_chunk=max_sentences_per_chunk, check_validity=check_validity)


    def fetch_relevent_info_from_documents(query_text, top_k=3, sql_where=None):
        data = self.documents_memeory.hybrid_query(query_text, top_k=top_k, sql_where=sql_where)
        self.add_context("The following was found in documentation uploaded by the user and may be relevent ... "+repr(data))







if __name__ == "__main__":

    OPENAI_API_KEY = "YOUR_API_KEY"

    agent = ChatAgent(name="Tomatio", api_key=OPENAI_API_KEY)
    agent.set_primary_directive("You are an A.I. assistant named Tomatio that wants to help users")

    while True:
        user_input = input("You: ")
        response = agent.send_message(user_input)
        print("Agent: " + response)
        if user_input.lower() in ["bye","goodbye"]:
            print("CHAT ENDED")
            break




























