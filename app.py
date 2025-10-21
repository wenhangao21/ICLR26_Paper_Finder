import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from chromadb.utils import embedding_functions as ef
import gradio as gr
import markdown
import ast
from sentence_transformers import SentenceTransformer


client = chromadb.PersistentClient(path="data/ICLR2026")
_ = SentenceTransformer("all-MiniLM-L6-v2")
# --- dynamic embedding selector ---
def get_collection(model_name: str, api_key: str):
    if model_name == "gemini-embedding-001":
        embedding_fn = ef.GoogleGenerativeAiEmbeddingFunction(api_key=api_key)
        COLLECTION_NAME = "Gemini"
    elif model_name == "all-MiniLM-L6-v2":
        embedding_fn = ef.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        COLLECTION_NAME = "MiniLM"
    else:
        raise ValueError(f"Unknown model: {model_name}")
    return client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)


def query_db(model_name, api_key, query_text, total_results=50):
    if not query_text.strip():
        return None, "Please enter a query."
    if model_name == "gemini-embedding-001" and not api_key.strip():
        return None, "Please enter your Gemini API key."

    try:
        collection = get_collection(model_name, api_key)
        results = collection.query(query_texts=[query_text], n_results=int(total_results))
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        ids = results["ids"][0]
        dists = results["distances"][0]

        records = []
        for doc_id, doc, meta, dist in zip(ids, docs, metas, dists):
            title = meta.get("title", "Untitled")
            keywords_raw = meta.get("keywords", "")
            pdf = meta.get("pdf", "")
            bibtex = meta.get("_bibtex", "")
            similarity = round(1 - dist, 4) if dist <= 1 else round(dist, 4)

            try:
                if isinstance(keywords_raw, str) and keywords_raw.strip().startswith("["):
                    keywords = ast.literal_eval(keywords_raw)
                elif isinstance(keywords_raw, list):
                    keywords = keywords_raw
                else:
                    keywords = [str(keywords_raw)]
            except Exception:
                keywords = [str(keywords_raw)]

            records.append({
                "title": title,
                "keywords": keywords,
                "pdf": pdf,
                "abstract_md": doc.strip(),
                "bibtex": bibtex,
                "similarity": similarity
            })
        return records, None
    except Exception as e:
        return None, f"Error: {e}"


def render_page(records, page, per_page=10):
    if not records:
        return "<p>No results to show.</p>"
    total_pages = (len(records) - 1) // per_page + 1
    page = max(1, min(page, total_pages))
    start, end = (page - 1) * per_page, min(page * per_page, len(records))
    html = ""
    for r in records[start:end]:
        abstract_html = markdown.markdown(r["abstract_md"], extensions=["fenced_code", "tables"])
        keyword_html = " ".join([
            f"<span class='keyword'>{k.strip().title()}</span>"
            for k in r["keywords"] if k and isinstance(k, str)
        ])
        html += f"""
        <div class='paper-card'>
            <h3>{r['title']}</h3>
            <p><b>Affinity Score:</b> {r['similarity']}</p>
            <p><b>Keywords:</b> {keyword_html}</p>
            <p><b>PDF:</b> <a href='{r['pdf']}' target='_blank'>{r['pdf']}</a></p>
            <details><summary>Show Abstract</summary>
              <div class='abstract markdown-body'>{abstract_html}</div>
            </details>
            <details><summary>Show BibTeX</summary>
              <div class='bibtex'><pre>{r['bibtex']}</pre></div>
            </details>
        </div>"""
    html += f"<div class='page-info'>Page {page} / {total_pages}</div>"
    return html


# --- UI ---
with gr.Blocks(title="ICLR 2026 Paper Search") as demo:
    gr.Markdown("## ICLR 2026 Paper Search")
    gr.Markdown("Semantic search over ICLR 2026 submissions.")

    with gr.Accordion("Search Options", open=True) as search_box:
        with gr.Row():
            model_dropdown = gr.Dropdown(
                label="Embedding Model",
                choices=["gemini-embedding-001", "all-MiniLM-L6-v2"],
                value="all-MiniLM-L6-v2",
                interactive=True
            )
            api_key_box = gr.Textbox(
                label="API Key (required for some embedding models)",
                type="password",
                placeholder="Enter Gemini API key",
                visible=False
            )
        total_results = gr.Number(label="Total number of results to retrieve", value=50, precision=0)
        query = gr.Textbox(label="Query (abstract of a paper)", placeholder="e.g., diffusion models in text-to-image generation", lines=2)
        search_btn = gr.Button("Search")

    results_box = gr.HTML("<p>Results will appear here.</p>")
    records_state, page_state = gr.State([]), gr.State(1)

    # hide/show api key dynamically
    def toggle_key(model_name):
        return gr.update(visible=(model_name == "gemini-embedding-001"))
    model_dropdown.change(toggle_key, inputs=model_dropdown, outputs=api_key_box)

    def on_search(model, key, q, total_res):
        recs, err = query_db(model, key, q, total_res)
        if err:
            return gr.update(open=True), f"<p style='color:red;'>{err}</p>", [], 1
        return gr.update(open=False), render_page(recs, 1), recs, 1

    search_btn.click(on_search,
        inputs=[model_dropdown, api_key_box, query, total_results],
        outputs=[search_box, results_box, records_state, page_state])

    with gr.Row():
        prev_btn = gr.Button("Previous")
        next_btn = gr.Button("Next")

    def change_page(records, page, direction):
        new_page = page + direction
        return render_page(records, new_page), new_page

    prev_btn.click(change_page,
        inputs=[records_state, page_state, gr.Number(value=-1, visible=False)],
        outputs=[results_box, page_state])
    next_btn.click(change_page,
        inputs=[records_state, page_state, gr.Number(value=1, visible=False)],
        outputs=[results_box, page_state])

    gr.HTML("""
    <style>
    #component-1{max-width:950px;margin:auto;}
    .paper-card{background:#fff;border-radius:10px;padding:16px;margin-bottom:18px;
                box-shadow:0 2px 8px rgba(0,0,0,0.1);}
    .keyword{display:inline-block;background:#e8f1ff;color:#003d99;border-radius:6px;
             padding:2px 8px;margin:2px;font-size:13px;}
    details summary{cursor:pointer;font-weight:600;color:#0066cc;}
    .abstract,.bibtex{background:#f8f8f8;padding:10px;border-radius:6px;margin-top:8px;}
    pre{background:#f9f9f9;border:1px solid #ddd;padding:8px;border-radius:4px;overflow-x:auto;}
    .page-info{text-align:center;font-weight:bold;margin-top:10px;}
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>
    <script>
      const obs=new MutationObserver(()=>{if(window.renderMathInElement)
        renderMathInElement(document.body,{delimiters:[
          {left:'$$',right:'$$',display:true},
          {left:'$',right:'$',display:false}]});});
      obs.observe(document.body,{childList:true,subtree:true});
    </script>
    """)

demo.launch()
