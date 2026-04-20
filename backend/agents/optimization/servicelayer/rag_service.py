import pandas as pd
import numpy as np
import faiss
import os
import json
from sentence_transformers import SentenceTransformer

# Paths for data and persistence
FILE_PATH = r"D:\Documents\EDDI-Chatbot\backend\agents\optimization\Process_Mining_Action_Engine.xlsx"
INDEX_CACHE = r"D:\Documents\EDDI-Chatbot\backend\agents\optimization\faiss_index.bin"
METADATA_CACHE = r"D:\Documents\EDDI-Chatbot\backend\agents\optimization\metadata.json"

def initialize_kb():
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # --- STEP 1: CHECK FOR CACHED DATA ---
    if os.path.exists(INDEX_CACHE) and os.path.exists(METADATA_CACHE):
        print("🚀 Loading Knowledge Base from Cache (Fast Start)...")
        index = faiss.read_index(INDEX_CACHE)
        with open(METADATA_CACHE, 'r') as f:
            metadata = json.load(f)
    else:
        # --- STEP 2: IF NO CACHE, LOAD EXCEL ---
        print(f"🔄 Cache not found. Loading Excel from: {FILE_PATH}")
        if not os.path.exists(FILE_PATH):
            print(f"❌ Error: File not found at {FILE_PATH}")
            return None

        df_raw = pd.read_excel(FILE_PATH, header=None)

        try:
            # Find header row containing 'RuleID'
            idx = df_raw[df_raw.apply(lambda r: r.astype(str).str.contains('RuleID').any(), axis=1)].index[0]
            df = df_raw.iloc[idx:].copy()
            df.columns = df.iloc[0]
            df = df.iloc[1:].reset_index(drop=True)
        except Exception as e:
            print(f"❌ Header Parsing Error: {e}")
            return None

        chunks, metadata = [], []
        print("✂️ Chunking data and generating embeddings...")
        
        for i, row in df.iterrows():
            trigger = str(row.get('Trigger (Watchman Agent Logic)', ''))
            if not trigger or any(x in trigger.lower() for x in ['nan', 'trigger']):
                continue

            chunk_text = f"Problem: {row.get('Category')}. Scenario: {trigger}"
            chunks.append(chunk_text)
            
            metadata.append({
                "rule_id": str(row.get('RuleID')),
                "category": str(row.get('Category')),
                "trigger": trigger,
                "action": str(row.get('Actionable Insight / Automation Script'))
            })

        # EMBEDDING & INDEXING
        embeddings = model.encode(chunks, show_progress_bar=True)
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(embeddings).astype('float32'))

        # --- STEP 3: SAVE TO CACHE ---
        faiss.write_index(index, INDEX_CACHE)
        with open(METADATA_CACHE, 'w') as f:
            json.dump(metadata, f)
        print(f"💾 Knowledge Base cached to disk for faster loading.")

    print(f"✅ Success! Knowledge Base Ready with {len(metadata)} rules.")

    # --- SEARCH FUNCTION ---
    def search(query, k=1):
        query_vec = model.encode([query])
        distances, indices = index.search(np.array(query_vec).astype('float32'), k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx < len(metadata):
                res = metadata[idx].copy()
                res['score'] = float(dist)
                results.append(res)
        return results

    return search

# --- STANDALONE TEST ---
if __name__ == "__main__":
    search_func = initialize_kb()
    if search_func:
        print("\n🔍 TESTING RAG SEARCH...")
        test_query = "slow query with many joins and sequential scan"
        matches = search_func(test_query, k=1)
        if matches:
            print(f"\n🎯 Best Match Found:\n{json.dumps(matches[0], indent=4)}")