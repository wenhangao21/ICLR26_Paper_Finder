# Semantic Search Across AI Venues

*TL;DR:* A tool that retrieves semantically similar papers from selected AI venues, including but not limited to recent ICML, ICLR, NeurIPS, CVPR, and over 17,000 ICLR 2026 submissions.

🔗 **Try It: [AI Paper Finder Web Interface](https://b67491c9b7c1a4f083.gradio.live)**

🌐 **Permanent Hosting Site: [http://ai-paper-finder.info/](http://ai-paper-finder.info/)** 

(Mainland China cannot access the permanent website. Please bookmark the repo and use the first link — we will update it regularly. 中国大陆无法访问永久网站，请收藏Repo使用第一个链接，我们会定期更新)

**Demo**

![Demo GIF](AI_paper_finder_demo.gif)

**We're still in beta and expanding the list of supported venues! We may update the beta version with new links updated here, so please save and star [this GitHub repo](https://github.com/wenhangao21/ICLR26_Paper_Finder) for future reference before the stable release.**

- There are already some tools avalible, e.g. [Paper Digest](https://www.paperdigest.org/). However,
	- ICLR 2026 submissions are not included yet.
	- Most existing tools rely mainly on keyword-based search, whereas we enable searches using full paper abstracts.
	- Why abstracts? They contain much richer information than titles or keywords.


You can ACTUALLY build your own Paper Finder in less than 30 minutes. See `Tutorial_Making_Paper_Recommenders.ipynb` in this repo.

💡 **Support us:**

* ⭐ [Star our GitHub repo](https://github.com/wenhangao21/ICLR26_Paper_Finder)
* 🔗 Share our tool on [LinkedIn](https://www.linkedin.com/in/wenhan-gao-2311611b4/) and [X](https://x.com/Wenhanacademia)
* ☕ [Buy us a coffee](https://buymeacoffee.com/wenhanacado)

**What's New Compared to ICLR 2026 Paper Finder?**
- 🧭 Expanded Venue Support
- 🌍 Multi-lingual Support *(performance is suboptimal compared to English)*
- 💡 Upgraded Local Embedding Model (Gemini removed now)

## What We’re Working On

We are currently:

* Expanding the list of supported venues
* Designing improved user interfaces
* Researching advanced paper-matching algorithms
* Developing multi-agent–supported search capabilities
* Enabling batch input and batch output
* Exploring researcher-specific personalization features (researcher persona)

## Contact and Outreach

**Project Lead**: [Wenhan Gao](https://wenhangao21.github.io/)

**Main Contributors**: [Wenhan Gao](https://wenhangao21.github.io/), [Jingxiang Qu](https://qujx.github.io/)

We are PhD students doing AI research, and it’s hard to afford servers to host this tool.

We’re currently seeking affordable server options, contact us if you have any suggestions.



## 🚀 ICLR_2026 Paper Finder
This project started as a finder designed specifically for only the ICLR 2026 submissions. We provide the open source implementation as it serves as a good reference for building your own AI Paper Recommender.

### 📓 Guideline for Building Your Own Recommender
Follow along with `Tutorial_Making_Paper_Recommenders.ipynb`. 

### 📓 Jupyter Notebook for Online Deployment
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

> **After running** `app.py`, **Gradio** will display a local URL. Simply open it in your web browser.

## Acknowledgement
If you find any bugs or have suggestions, feel free to [contact me](https://wenhangao21.github.io/).
My collaborator [Jingxiang Qu](https://qujx.github.io/), my undergraduate mentee [Yichi Zhang](https://yichixiaoju.github.io/YichiZhang.github.io/), and I (and GPT) are actively working on expanding this system, adding support for more venues, improving search mechanisms with specific models, introducing multi-agent support, and introducing new functionalities.

If you're interested in collaborating or contributing, we’d be very happy to hear from you!

Thanks for your interests! You are the ![Badge](https://hitscounter.dev/api/hit?url=https%3A%2F%2Fgithub.com%2Fwenhangao21%2FICLR26_Paper_Finder&label=Paper_Finder&icon=book-half&color=%239ec5fe&message=&style=flat&tz=UTC) user of Paper Finder.


