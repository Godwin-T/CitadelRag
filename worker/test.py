# from pathlib import Path
# from loguru import logger
# from app.services.storage import resolve_to_local_path


# local_path = resolve_to_local_path("s3://citadel-docs/uploads/97aa50f1-5ac6-4c9b-9488-81682cf017ea-THE-INTELLIGENT-INVESTOR.pdf")
# file_path = Path(local_path)
# logger.info(f"local path: {local_path}")
# suffix = Path(local_path).suffix.lower()
# logger.info(f"extracting text | path={file_path} suffix={suffix}")


from urllib import response

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()

# List of texts (the first 5 in your list)
texts = [
    "THE \nINTELLIGENTINVESTOR\nA BOOK OF PRACTICAL COUNSEL\nREVISED EDITION\nBENJAMIN GRAHAM\nUpdated with New Commentary by Jason Zweig\nTo E.M.G.\nThrough chances various, through all \nvicissitudes, we make our way ....\nAeneid\nContents\nEpigraph iii\nPreface to the Fourth Edition, by Warren E. BuffettANote About Benjamin Graham, by Jason Zweigx\nIntroduction: What This Book Expects to Accomplish 1\nCOMMENTARY ON THE INTRODUCTION 12\n1. Investment versus Speculation: Results to Be \nExpected by the Intelligent Investor 18",
    "COMMENTARY ON CHAPTER 1 35\n2. The Investor and Inflation 47\nCOMMENTARY ON CHAPTER 2 58\n3. A Century of Stock-Market History: \nThe Level of Stock Prices in Early 1972 65\nCOMMENTARY ON CHAPTER 3 80\n4. General Portfolio Policy: The Defensive Investor 88\nCOMMENTARY ON CHAPTER 4 101\n5. The Defensive Investor and Common Stocks 112\nCOMMENTARY ON CHAPTER 5 124\n6. Portfolio Policy for the Enterprising Investor: \nNegative Approach 133",
    "COMMENTARY ON CHAPTER 6 145\n7. Portfolio Policy for the Enterprising Investor: \nThe Positive Side 155\nCOMMENTARY ON CHAPTER 7 179\n8. The Investor and Market Fluctuations 188\nivviii\nv Contents\nCOMMENTARY ON CHAPTER 8 213\n9. Investing in Investment Funds 226\nCOMMENTARY ON CHAPTER 9 242\n10. The Investor and His Advisers 257\nCOMMENTARY ON CHAPTER 10 272",
    "11. Security Analysis for the Lay Investor: \nGeneral Approach 280\nCOMMENTARY ON CHAPTER 11 302\n12. Things to Consider About Per-Share Earnings 310\nCOMMENTARY ON CHAPTER 12 322\n13. A Comparison of Four Listed Companies 330\nCOMMENTARY ON CHAPTER 13 339\n14. Stock Selection for the Defensive Investor 347\nCOMMENTARY ON CHAPTER 14 367\n15. Stock Selection for the Enterprising Investor 376\nCOMMENTARY ON CHAPTER 15 396",
    "16. Convertible Issues and Warrants 403\nCOMMENTARY ON CHAPTER 16 418\n17. Four Extremely Instructive Case Histories 422\nCOMMENTARY ON CHAPTER 17 438\n18. A Comparison of Eight Pairs of Companies"
]

responses = client.embeddings.create(
  model="text-embedding-ada-002",
  input=texts,
  encoding_format="float"
)

print(responses.data[0].embedding)
