import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_docling import DoclingLoader
from langchain_milvus import Milvus

load_dotenv()

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
vectorstore = Milvus(
    embedding_function=embeddings,
    collection_name="clinicalGuides",
    connection_args={"uri": "https://in03-5a9f451583761f1.serverless.gcp-us-west1.cloud.zilliz.com", "token": os.getenv("MILVUS_TOKEN") , "db_name": "enarmy"},
    index_params={"index_type": "FLAT", "metric_type": "L2"},
    consistency_level="Strong",
    drop_old=False,  # set to True if seeking to drop the collection with that name if it exists
)

# Load and chunk content
FILE_PATH = "./data/081GER_1.pdf"
loader = DoclingLoader(file_path=FILE_PATH)
docs = loader.load()

# Index chunks
_ = vectorstore.add_documents(documents=docs)