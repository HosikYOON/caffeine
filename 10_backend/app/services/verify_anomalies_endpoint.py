
import httpx
import asyncio

URL = "http://localhost:8001/api/anomalies"

async def verify():
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"GET {URL}...")
            response = await client.get(URL)
            print(f"Status: {response.status_code}")
            data = response.json()
            print(f"Count: {len(data)}")
            if len(data) > 0:
                print("First item:", data[0])
            else:
                print("No anomalies returned.")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
