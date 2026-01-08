# Airmini Backend

AI travel assistant API. Takes travel questions, figures out what data sources to check (visa APIs, web search, knowledge base), and streams back an answer. Built with FastAPI and LangGraph.

## Why I Built This

Most AI chatbots are just prompt → LLM → response. That works for general knowledge, but travel questions need real data. "Do I need a visa for Japan?" depends on your nationality, and that info changes. You can't trust an LLM's training data for that.

So the interesting problem: how do you build a system that knows when to check external sources, which sources to check, and how to combine the results into a coherent answer? That's what LangGraph is for.

## Tech Decisions

### LangGraph for Orchestration

LangGraph lets you define AI workflows as a graph — nodes are steps, edges are transitions. Instead of one prompt, you have a pipeline:

```
receive_message → classify → dispatch_sources → generate_response → validate → stream
```

The `classify` node is an LLM call that looks at the question and decides: does this need visa info? Web search? The knowledge base? All three? It returns a list of sources to query.

Then `dispatch_sources` fans out to multiple nodes in parallel — visa API, Tavily search, RAG retrieval. Results get aggregated and passed to `generate_response`.

Why not just stuff everything into one prompt? Token limits, latency, and accuracy. If I retrieve 10 documents from RAG, 5 web results, and visa data, that's a lot of context. Classification lets me only fetch what's relevant.

### RAG with pgvector

I have a knowledge base of travel documents — TSA rules, airline policies, airport guides. These are chunked, embedded, and stored in Postgres with the pgvector extension.

When a question comes in and the classifier says "check knowledge base," the RAG node:

1. Embeds the query with OpenAI's embedding model
2. Does a similarity search against the vector store
3. Returns the top N relevant chunks

Postgres might seem weird for vectors (why not Pinecone?), but I already have Postgres for chat history. One fewer service to manage. pgvector is fast enough for this scale.

### Document Ingestion Pipeline

Getting documents into the vector store is its own thing. The ingestion script handles:

- **PDFs** — Extracted with OCR fallback for scanned docs
- **Web pages** — Crawled with crawl4ai (headless browser, handles JS-rendered content)
- **Text files** — Straightforward

Each document gets chunked (overlapping windows), embedded, and inserted. Metadata tracks the source URL so the LLM can cite it.

I pre-loaded TSA regulations, CATSA (Canadian security), and policies from Delta, United, Air Canada, Korean Air. Adding new sources is just running the ingestion script with a URL or file path.

### Visa API Integration

RapidAPI has a visa checker service. You give it origin country, destination country, nationality — it tells you visa requirements. Way more reliable than asking an LLM to remember visa rules from its training data.

The visa node calls this API, parses the response, and formats it for the LLM context. If the API fails or returns garbage, the node returns empty and the system falls back to web search.

### Web Search with Tavily

For questions that need current info — "best time to visit Bali" or "COVID restrictions in Thailand" — I use Tavily. It's a search API built for LLMs, returns clean results without the SEO spam.

The web search node queries Tavily, extracts the relevant snippets, and includes source URLs. The LLM can then synthesize an answer and cite where the info came from.

### Response Validation Loop

Here's the clever bit. After generating a response, there's a `relevance_check` node that evaluates: did we actually answer the question? Is the response coherent? If not, it retries with different sources — up to 5 times.

This catches cases where the classifier made a bad call. Asked about visa requirements but classified it as general knowledge? First response will be vague, validation fails, retry with visa API enabled.

Most questions resolve in 1-2 iterations. The retry loop is a safety net, not the happy path.

### Streaming with SSE

Responses stream token-by-token via Server-Sent Events. The frontend opens a connection, and as the LLM generates text, it flows through.

LangGraph supports streaming natively. Each node can yield intermediate results. I use this to stream "thought phases" — what the system is doing at each step — before the final response starts.

```python
async for event in workflow.astream(state):
    if event.type == "thought":
        yield f"data: {json.dumps({'type': 'thought', 'phase': event.phase})}\n\n"
    elif event.type == "token":
        yield f"data: {json.dumps({'type': 'token', 'content': event.content})}\n\n"
```

### Trip Context

The frontend sends trip details — nationality, destination, dates, cabin class. This gets stored per-chat and injected into every LLM call as system context.

```
The user is a US citizen traveling from New York to Tokyo 
on March 15, 2025, flying business class for leisure.
```

Now the LLM doesn't have to ask clarifying questions. It just knows.

### Auth with Clerk (Optional)

Chat streaming works without auth — anonymous users get full functionality. But if you want chat history persistence, you need to sign in.

Clerk JWTs come in the Authorization header. The backend verifies them against Clerk's public keys. If valid, requests get associated with a user ID. If not, it's anonymous mode.

Anonymous mode still works, you just don't get saved chats. Good for trying the product without commitment.

## The LangGraph Workflow

```
START
  ↓
receive_message (parse input, load trip context)
  ↓
classify (LLM decides: visa? web? rag? combination?)
  ↓
dispatch_sources (parallel fan-out)
  ├→ visa_search (RapidAPI)
  ├→ web_search (Tavily)
  └→ rag_search (pgvector)
  ↓
generate_response (LLM synthesizes from sources)
  ↓
relevance_check (is this a good answer?)
  ├→ NO: retry (back to classify, max 5x)
  └→ YES: stream_final_response
  ↓
END
```

Each node is a Python async function. LangGraph handles the execution order, parallelism, and state passing.

## Stuff I Learned

**LangGraph state management is tricky** — The graph passes a state object between nodes. If you mutate it wrong, you get weird bugs. I ended up using immutable updates everywhere.

**Embedding models matter** — Started with a cheaper embedding model, retrieval quality was mediocre. Switched to `text-embedding-3-small` and it got noticeably better. The cost difference is pennies.

**Retry loops need escape hatches** — The validation retry loop can get stuck if the question is genuinely unanswerable. Had to add logic to detect "we've tried everything, just give the best response we have."

**SSE and CORS are annoying** — Streaming works differently than regular HTTP. Had to configure CORS specifically for SSE connections, and some proxies buffer the stream (breaks the real-time feel).

## Stack

| What | Why |
|------|-----|
| FastAPI | Async, fast, good for streaming |
| LangGraph | Workflow orchestration for multi-step AI |
| OpenAI GPT-4o-mini | Good enough, cheaper than GPT-4 |
| PostgreSQL + pgvector | Vector storage without another service |
| SQLAlchemy (async) | ORM that doesn't block |
| Alembic | Database migrations |
| Tavily | Web search built for LLMs |
| crawl4ai | Web scraping for document ingestion |
| Clerk | Auth without building it myself |
