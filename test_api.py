import subprocess
import time
import requests

def run_test():
    print("[Step 1] Starting local FastAPI server for testing...")
    # 后台启动 uvicorn
    proc = subprocess.Popen(
        ["D:\\zero_cost_income\\venv310\\Scripts\\python.exe", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待服务器启动
    time.sleep(3)
    
    test_url = "https://example.com"
    print(f"[Step 2] Sending test request to extract URL: {test_url} ...")
    
    try:
        response = requests.get(
            "http://127.0.0.1:8000/api/to-markdown",
            params={"url": test_url, "include_images": True},
            timeout=10
        )
        print(f"[Step 3] Received status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("[+] Test succeeded! Data extraction results:")
            print(f"Title: {data.get('title')}")
            print(f"Meta Description: {data.get('description')}")
            print(f"Markdown Character Length: {len(data.get('markdown'))}")
            print("\n--- Markdown Preview ---")
            print(data.get('markdown')[:300] + "\n...")
            print("--------------------\n")
        else:
            print(f"[-] Test failed! Response: {response.text}")
            
    except Exception as e:
        print(f"[-] Exception occurred: {str(e)}")
    finally:
        print("[Step 4] Shutting down local server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
            print("[+] Server closed successfully")
        except subprocess.TimeoutExpired:
            proc.kill()
            print("[!] Server killed forcefully")

if __name__ == "__main__":
    run_test()

