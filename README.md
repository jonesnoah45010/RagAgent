


# ChatAgent

ChatAgent is a Python class designed to interact with OpenAI's GPT-based APIs. It allows for seamless conversation management, token counting, and dynamic session refreshes to handle token limits. The `ChatAgent` class is equipped with features to track conversation history, summarize ongoing conversations, and send auxiliary queries without impacting the main session context.

## Features

-   **Primary Directive:** Set a system prompt to guide the assistant's behavior throughout the session.
    
-   **Token Management:** Tracks token usage and ensures conversations stay within predefined token limits.
    
-   **Session Refresh:** Automatically summarizes and refreshes conversations when nearing token limits.
    
-   **Async Support:** Send asynchronous messages and side queries using asyncio.
    
-   **Contextual and Side Messages:** Send context-dependent or independent queries without altering the main conversation history.
    
-   **Conversation Summarization:** Summarize conversation history dynamically with a user-defined word limit.
    

----------

## Prerequisites

-   Python 3.8+
    
-   OpenAI Python library
    
-   tiktoken library
    

To install the required packages, run:

```
pip install openai tiktoken asyncio
```

----------

## Installation

1.  Clone this repository:
    

```
git clone https://github.com/yourusername/chatagent.git
```

2.  Navigate to the project directory:
    

```
cd chatagent
```

3.  Install dependencies:
    

```
pip install -r requirements.txt
```

----------

## Usage

### Initialization

```
from chat_agent import ChatAgent

# Initialize the ChatAgent
agent = ChatAgent(api_key="your_openai_api_key")

# Set a primary directive
agent.set_primary_directive("You are a helpful assistant.")
```

### Sending Messages

Send messages and receive AI responses:

```
response = agent.send_message("Tell me three fun facts about frogs.")
print(response)
```

### Token Management

-   Check the number of tokens used:
    
    ```
    print(agent.count_tokens())
    ```
    
-   Check remaining tokens:
    
    ```
    print(agent.tokens_left())
    ```
    

### Refreshing the Session

Automatically summarize and refresh conversation when approaching the token limit:

```
agent.refresh_session()
```

### Asynchronous Messaging

Send asynchronous messages using asyncio:

```
import asyncio

async def main():
    response = await agent.send_message_async("Tell me a joke.")
    print(response)

asyncio.run(main())
```

### Side Messages

Get responses for side queries without affecting the main conversation history:

```
response = agent.side_message("What is the capital of Canada?", use_context=False)
print(response)
```

### Conversation Summarization

Summarize the current conversation:

```
summary = agent.summarize_current_conversation(in_max_n_words=100)
print(summary)
```

----------

## Example

```
if __name__ == "__main__":
    OPENAI_API_KEY = "your_openai_api_key"

    agent = ChatAgent(api_key=OPENAI_API_KEY)
    agent.set_primary_directive("You are an enthusiastic assistant.")
    response = agent.send_message("What are the best practices for Python programming?")
    print(response)
```

----------

## Notes

-   Replace `your_openai_api_key` with your actual OpenAI API key.
    
-   The `tiktoken` library is used for token counting and must support the specified model.
    

----------

## License

This project is licensed under the MIT License. See the LICENSE file for details.

----------

