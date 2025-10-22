# ICLR26 Paper Finder

ICLR26 Paper Finder is a lightweight tool intended to help users search, filter, and explore relavent to their research. 

🔗 **[ICLR2026 Paper Finder on Hugging Face](https://huggingface.co/spaces/wenhanacademia/ICLR2026_PaperFinder)**

- There are already some tools avalible, e.g. [Paper Digest](https://www.paperdigest.org/). However,
	- ICLR 2026 submissions are not included yet.
	- Mainly keyword-based search only, not allowing semantic search through information-rich and context-aware abstracts.
	- A tutorial has been added (`Tutorial_Making_Paper_Recommenders.ipynb`). You can build your own ICLR Paper Finder in less than 30 minutes. 
	

- My collaborator, [Jingxiang Qu](https://qujx.github.io/), is currently developing code to collect and process papers from venues beyond ICLR. Stay tuned, we’ll 
upload the data processing scripts soon, so you can run the recommender on these additional venues with only minimal modifications to the code (sorry, we don't have a powerful server to host an app for all these venues).

	
> ⚠️ Note: The web interface may freeze on Hugging Face.
> If that happens, simply refresh the page to continue using the app (I'm too poor to afford a server). 

## 🚀 How to use
We offer 3 options: through the live web interface, a Jupyter Notebook that you can run locally or on Google Colab for free, or a Python script on your local terminal.

We currently support only ICLR 2026 with two embedding models: `gemini-embedding-001` and `all-MiniLM-L6-v2` (free). **My collaborators and I are making efforts to expand the venues and embedding models it supports.**

- `all-MiniLM-L6-v2`: A totally free small local embedding model with approximately 22 million parameters, a base size of about 80 MB, and a minimum memory requirement of around 4 GB RAM for inference. It runs fast even without GPUs.

- `gemini-embedding-001`: An embedding model provided by Google AI. **Each inference costs less than $0.000075**. Building embeddings for all ICLR 2026 submitted papers costs less than $1.50. [Refer to Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing?authuser=5#standard_10).

> ⚠️ Note: Your API key is completely secure if you choose to use the Gemini embedding model. The source code is available on Hugging Face.


### 🌐 Live Web Interface

We host the app on **Hugging Face Spaces**:

🔗 **[ICLR2026 Paper Finder on Hugging Face](https://huggingface.co/spaces/wenhanacademia/ICLR2026_PaperFinder)**

> ⚠️ Note: The web interface may freeze on Hugging Face.
> If that happens, simply refresh the page to continue using the app. 


### 📓 Jupyter Notebook
Follow along with `ICLR2026_Paper_Finder.ipynb`. 

### 💻 Python Script on Your Local Terminal
- Setup the anaconda (skip this if you already have conda)
```bash
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm ~/miniconda3/miniconda.sh
source ~/miniconda3/bin/activate
```

- Create a conda enviroment (skip this if you want to just install on your base enviroment)
```bash
conda create -n PaperFinder python=3.12
conda deactivate # Make sure no other conda enviroment is activated
conda activate PaperFinder
```

-  Install the required python packages
```bash
pip install gdown
pip install chromadb
pip install gradio
pip install markdown
pip install google-generativeai
pip install sentence_transformers
```
- Download processed data
```bash
gdown https://drive.google.com/uc?id=1RTKWZ4qY4X2mW5BorZOrWTOb2fCipIhr
unzip ICLR2026.zip
```	

- Initiate the application
```bash
python app.py
```	

> **After running** `aaa.py`, **Gradio** will display a local URL. Simply open it in your web browser.

## Acknowledgement
If you find any bugs or have suggestions, feel free to [contact me](https://wenhangao21.github.io/).
My collaborator [Jingxiang Qu](https://qujx.github.io/), my undergraduate mentee [Yichi Zhang](https://yichixiaoju.github.io/YichiZhang.github.io/), and I (and GPT) are actively working on expanding this system, adding support for more venues, improving search mechanisms with specific models, introducing multi-agent support, and introducing new functionalities.

If you're interested in collaborating or contributing, we’d be very happy to hear from you!


