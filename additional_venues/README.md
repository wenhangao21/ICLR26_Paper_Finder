📢 **Stay tuned** — With the extension of venues, we'll release more scripts that collect paper information and process it into the same format used in the tutorial for your convenience. 

🗂️ **List of processed venues:**
  - ICML
  - ICLR
  - NeurIPS
  - CVPR
  - ICCV

**For ICML/ICLR/NeurIPS:** 
```bash
# For example, obtaining all paper information submitted to ICLR 2025
python ICML_ICLR_NeurIPS.py --conf_name ICLR --year 2025 --email <Your Openreview Email> --password <Your Openreview Password> --state <'Submitted' or 'Accepted'>
```

**For CVPR/ICCV:** 
```bash
# For example, obtaining all paper information accepted by CVPR 2025
python CVPR_ICCV.py --conf_name CVPR --year 2025 
```

Due to different obtaining methods (API-based or crawler-based), obtaining papers from openreview (ICLR/ICML/NeurIPS) will be much faster than others.

🙏 **Acknowledgement:** All data processing work was done by my collaborator, [Jingxiang Qu](https://qujx.github.io/).
