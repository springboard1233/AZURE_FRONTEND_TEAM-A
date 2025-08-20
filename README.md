# AZURE_FRONTEND_TEAM-A

# Azure Demand Forecasting – Milestone 1

This project forecasts Azure Compute & Storage demand using ML models. This milestone focuses on data collection and preparation.

## Contents
- Azure usage data (simulated)
- External factors (economic indicators)
- Jupyter Notebooks for EDA & Cleaning
- Merged dataset ready for feature engineering

## Instructions
1. Clone the repo
2. Run notebooks in sequence
3. Submit cleaned CSV + screenshots of visualizations

## requirements.txt
pandas
numpy
matplotlib
seaborn
jupyter
openpyxl

## necessary docs
Dummy CSV files

Sample Jupyter notebook for 01_data_loading_eda.ipynb

EDA report template (eda_report.md)?

# 📝 EDA Report – Milestone 1

## 📅 Project: Azure Demand Forecasting  
**Milestone:** Data Collection & Preparation  
**Team:** [Team Name]  
**Date:** [Date]

---

## 1. 📂 Datasets Used
- `azure_usage.csv`: Simulated data for Azure Compute & Storage usage  
- `external_factors.csv`: Economic indicators and cloud market demand

## 2. 📊 Key Observations
### Azure Usage:
- Number of records: [X]  
- Regions covered: [List of regions]  
- Average CPU usage: [Value]  
- Average Storage usage: [Value]  
- Active users range: [Min - Max]

### External Data:
- Economic Index range: [Min - Max]  
- Market Demand: [Mean/Std]  
- Holidays: Weekend indicator included

## 3. 🧼 Data Quality Checks
| Column | Missing Values | Action Taken         |
|--------|----------------|----------------------|
| usage_cpu | 0 | N/A |
| usage_storage | 3 | Filled using forward fill |
| ... | ... | ... |

## 4. 📈 Visualizations
- Total CPU usage trend over time  
- Region-wise average usage bar chart  
- Correlation heatmap (if done)

## 5. 🧩 Merging External Data
Successfully merged internal and external datasets on `date`.

## 6. ✅ Final Output
Cleaned dataset saved at: `data/processed/cleaned_merged.csv`  
Ready for feature engineering.

---

## 📌 Notes / Challenges
- [Mention any issues faced]  
- [Ideas for improvement]


## FOLDER_STRUCTURE

azure-demand-forecasting/
│
├── data/
│   ├── raw/
│   │   ├── azure_usage.csv
│   │   └── external_factors.csv
│   └── processed/
│       └── cleaned_merged.csv
│
├── notebooks/
│   ├── 01_data_loading_eda.ipynb
│   └── 02_data_cleaning_merging.ipynb
│
├── scripts/
│   └── utils.py
│
├── reports/
│   └── eda_report.md
│
├── requirements.txt
└── README.md
