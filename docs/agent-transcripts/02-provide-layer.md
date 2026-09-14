Agent Transcript 02 — Provider Layer and Ollama

Objective

Introduce a replaceable chat-provider abstraction and implement a local Ollama provider so the application can use a local model without coupling the RAG layer to one specific LLM.

Agent direction

The provider layer was designed around a small interface:

ChatProvider
    ↓
OllamaChatProvider

The chat provider needed:

configurable base URL;

configurable chat model;

bounded request timeout;

structured response data;

controlled provider errors;

safe logging.

The embedding model was deliberately kept separate from the chat model.

Implementation outcome

The implementation added:

ChatProvider protocol

ChatResponse dataclass

ProviderError

OllamaChatProvider

configurable OLLAMA_BASE_URL

configurable OLLAMA_CHAT_MODEL

finite model timeout

safe error handling

provider tests

The local chat model used for development was:

phi3:latest

The embedding model remained:

nomic-embed-text:latest

Local verification

Ollama was already running on the development machine.

A direct API check was used to verify the server and available models.

Available models included:

nomic-embed-text:latest

phi3:latest

llama3:latest

A direct chat request to Ollama was also used to verify that phi3:latest could respond.

Failure encountered

Running:

ollama serve

returned an error equivalent to:

Error: listen tcp 127.0.0.1:11434: bind: address already in use

Correction

This was not treated as an application failure. It indicated that an Ollama server was already listening on the expected port.

Instead of starting a second server, the existing server was verified through its HTTP API.

Verification result

Provider tests passed and the provider implementation was integrated without changing the existing RAG interfaces.

Engineering principle

Embedding infrastructure and chat generation should remain independently replaceable. This allows a future cloud chat provider to be added without changing the vector representation or retrieval implementation.
