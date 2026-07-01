import asyncio
import httpx
import json
import time

API_URL = "http://localhost:8000/api/v1"
HEADERS = {"Content-Type": "application/json"}

async def main():
    async with httpx.AsyncClient() as client:
        print("1. Sending initial chat request...")
        response = await client.post(
            f"{API_URL}/chat",
            json={"message": "analyze linkedin trends and write a post about it"},
            headers=HEADERS,
            timeout=120.0
        )
        print(f"Chat status: {response.status_code}")
        chat_data = response.json()
        print(json.dumps(chat_data, indent=2))
        
        thread_id = chat_data.get("thread_id")
        
        # Wait a bit for drafts
        print("\n2. Getting pending actions...")
        time.sleep(2)
        
        # In a real app we might poll or get this from the chat response
        # The chat response might already say it's waiting for selection
        
        pending_resp = await client.get(f"{API_URL}/pending")
        pending_data = pending_resp.json()
        print(json.dumps(pending_data, indent=2))
        
        drafts = pending_data.get("data", {}).get("pending_drafts", [])
        if not drafts:
            print("No pending drafts found.")
            return
            
        first_draft = drafts[0]
        thread_id = first_draft.get("thread_id")
        draft_id = first_draft.get("drafts", [{}])[0].get("id", 1)
        
        print(f"\n3. Selecting draft {draft_id} for thread {thread_id}...")
        select_resp = await client.post(
            f"{API_URL}/drafts/select",
            json={
                "thread_id": thread_id,
                "selected_draft_id": draft_id
            },
            headers=HEADERS,
            timeout=120.0
        )
        print(f"Select status: {select_resp.status_code}")
        select_data = select_resp.json()
        print(json.dumps(select_data, indent=2))
        
        print("\n4. Final approving draft...")
        approve_resp = await client.post(
            f"{API_URL}/drafts/approve",
            json={
                "thread_id": thread_id,
                "approved": True
            },
            headers=HEADERS,
            timeout=120.0
        )
        print(f"Approve status: {approve_resp.status_code}")
        approve_data = approve_resp.json()
        print(json.dumps(approve_data, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
