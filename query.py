import os

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain import hub
from langchain_core.documents import Document
from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict
from langchain_milvus import Milvus
from langchain.chat_models import init_chat_model
import json

llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
vectorstore = Milvus(
    embedding_function=embeddings,
    collection_name="clinicalGuides",
    connection_args={"uri": "https://in03-5a9f451583761f1.serverless.gcp-us-west1.cloud.zilliz.com", "token": os.getenv("MILVUS_TOKEN") , "db_name": "enarmy"},
    index_params={"index_type": "FLAT", "metric_type": "L2"},
    consistency_level="Strong",
    drop_old=False,  # set to True if seeking to drop the collection with that name if it exists
)

# Define prompt for question-answering
# N.B. for non-US LangSmith endpoints, you may need to specify
# api_url="https://api.smith.langchain.com" in hub.pull.
prompt = hub.pull("rlm/rag-prompt")

# Define state for application
class State(TypedDict):
    question: str
    context: List[Document]
    answer: str

# Define application steps
def retrieve(state: State):
    retrieved_docs = vectorstore.similarity_search(state["question"])
    return {"context": retrieved_docs}

def generate(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    messages = prompt.invoke({"question": state["question"], "context": docs_content})
    response = llm.invoke(messages)
    return {"answer": response.content}

def clip_text(text, threshold=100):
    return f"{text[:threshold]}..." if len(text) > threshold else text

# Compile application and test
graph_builder = StateGraph(State).add_sequence([retrieve, generate])
graph_builder.add_edge(START, "retrieve")
graph = graph_builder.compile()

QUESTION = "explica Enfermedad inflamatoria pélvica"
response = graph.invoke({"question": QUESTION})

print(f"Question:\n{QUESTION}\n\nAnswer:\n{response['answer']}")

for i, doc in enumerate(response["context"]):
    print()
    print(f"Source {i + 1}:")
    print(f"  text: {json.dumps(clip_text(doc.page_content, threshold=350))}")
    for key in doc.metadata:
        if key != "pk":
            val = doc.metadata.get(key)
            clipped_val = clip_text(val) if isinstance(val, str) else val
            print(f"  {key}: {clipped_val}")