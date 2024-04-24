import os
import dotenv
from flask import Flask, render_template, request, jsonify
import sqlite3
import dotenv

# Load environment variables
dotenv.load_dotenv()
if "OPENAI_API_KEY" not in os.environ:
    raise Exception("OPENAI_API_KEY is not set in your .env file")

app = Flask(__name__)

# Import AI and database handling libraries
from langchain.storage import LocalFileStore
from langchain.embeddings import CacheBackedEmbeddings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores.chroma import Chroma
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains.query_constructor.base import AttributeInfo
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.chains import create_sql_query_chain
import ast

# Load documents from SQLite and create Chroma DB
conn = sqlite3.connect('videos.db')
cursor = conn.cursor()
cursor.execute("SELECT Title, Chapter FROM VideoChapters")
rows = cursor.fetchall()
titles = [row[0] for row in rows]
chapters = [row[1] for row in rows]
conn.close()

# Setup AI models and database
underlying_embeddings = OpenAIEmbeddings()
store = LocalFileStore("./cache/")
cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings, store, namespace=underlying_embeddings.model
)

class Document:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata
    def __repr__(self):
        return f"Document(page_content='{self.page_content}', metadata={self.metadata})"

docs = []
for title, chapter in rows:
    # Determine if the chapter is present
    has_chapter = chapter is not None
    
    # Create a Document object for each row
    doc = Document(
        page_content=f"Title: {title}, Chapter: {chapter if has_chapter else 'No chapter'}",
        metadata={"has_chapter": has_chapter}
    )
    docs.append(doc)

underlying_embeddings = OpenAIEmbeddings()
store = LocalFileStore("./cache/")
list(store.yield_keys())
cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings, store, namespace=underlying_embeddings.model
)

vectorstore = Chroma.from_documents(docs, embedding=cached_embedder)

#----------------------------------------------------------------------#

metadata_field_info = [AttributeInfo(name="has_chapter", description="Indicates whether the video title contains chapters.", type="boolean")]
document_content_description = "Titles of videos with their corresponding chapters."
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
retriever = SelfQueryRetriever.from_llm(
    llm,
    vectorstore,
    document_content_description,
    metadata_field_info,
    enable_limit=True,
    verbose=True,
    search_kwargs={"k": 2})

#----------------------------------------------------------------------#
@app.route('/')
def index():
    return render_template('index.html')

def extract_title_and_chapter(page_content):
    # Assuming the format is 'Title: <title>, Chapter: <chapter>'
    title_part, chapter_part = page_content.split(", Chapter: ")
    title = title_part.split("Title: ")[1]
    chapter = chapter_part if chapter_part != "No chapter" else None
    return title, chapter


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    first_result = retriever.invoke({"query": query})
    db = SQLDatabase.from_uri("sqlite:///videos.db")

    # Assuming this part of your Flask app handles the database query and response formatting
    sql_outputs = []
    for document in first_result:
        title, chapter = extract_title_and_chapter(document.page_content)
        sql_query = f"SELECT Title, Link FROM VideoChapters WHERE Title = '{title}' AND (Chapter = '{chapter}' OR Chapter IS NULL)"
        sql_output = db.run(sql_query)
        try:
            parsed_output = ast.literal_eval(sql_output)
            if isinstance(parsed_output, list):
                for record in parsed_output:
                    merged_answer = {"title": record[0], "link": record[1]}
                    sql_outputs.append(merged_answer)
            else:
                print(f"Unexpected format: {sql_output}")
        except (ValueError, SyntaxError):
            print(f"Could not parse output: {sql_output}")
    return jsonify(sql_outputs)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
