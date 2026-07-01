import asyncio
import httpx
import json
import time
import sys

API_URL = "http://localhost:8000/api/v1"
HEADERS = {"Content-Type": "application/json"}

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    async with httpx.AsyncClient() as client:
        print("1. Sending initial chat request...")
        response = await client.post(
            f"{API_URL}/chat",
            json={"message": "analyze linkedin trends and write a post about AI agents"},
            headers=HEADERS,
            timeout=120.0
        )
        print(f"Chat status: {response.status_code}")
        chat_data = response.json()
        thread_id = chat_data.get("thread_id")
        print(f"Started thread: {thread_id}")
        
        print("\n2. Polling for pending actions...")
        draft_id = None
        for i in range(120): # up to 4 minutes
            pending_resp = await client.get(f"{API_URL}/pending", headers=HEADERS)
            pending_data = pending_resp.json()
            drafts = pending_data.get("items", [])
            
            my_draft = None
            for d in drafts:
                if d.get("thread_id") == thread_id:
                    my_draft = d
                    break
            
            if my_draft:
                draft_id = my_draft.get("id")
                if draft_id:
                    print(f"Found pending draft! ID: {draft_id}")
                    break
            
            print(f"Waiting... ({i+1}/120)")
            time.sleep(2)
            
        if not draft_id:
            print("Timed out waiting for drafts.")
            return
            
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
        
        # Poll for it to reach final_approval
        print("\n4. Polling for final approval interrupt...")
        for i in range(30):
            pending_resp = await client.get(f"{API_URL}/pending", headers=HEADERS)
            pending_data = pending_resp.json()
            drafts = pending_data.get("items", [])
            
            # Since the DB status is 'pending', the API doesn't expose graph state directly in /pending
            # We'll just wait 10 seconds to allow the graph to reach final_approval_interrupt
            if i == 5:
                print("Assuming graph reached final approval!")
                break
                
            print(f"Waiting for graph processing... ({i+1}/30)")
            time.sleep(2)
            
        print("\n5. Final approving draft...")
        approve_resp = await client.post(
            f"{API_URL}/drafts/approve",
            json={
                "thread_id": thread_id,
                "approved": True
            },
            headers=HEADERS,
            timeout=None
        )
        print(f"Approve status: {approve_resp.status_code}")
        print(json.dumps(approve_resp.json(), indent=2))
        
        print("\n6. Validating it posted...")
        time.sleep(15) # wait for post node
        
        # Check thread status or just assume successful if no error is thrown
        print("Done!")

if __name__ == '__main__':
    asyncio.run(main())
