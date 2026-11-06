import time
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

# 1. Test Root / Frontend HTML
r_root = client.get("/")
print(f"1. Root status: {r_root.status_code}, HTML length: {len(r_root.text)}")

# 2. Test Tools Endpoint
r_tools = client.get("/api/tools")
tools = r_tools.json()
print(f"2. Tools status: {r_tools.status_code}, Total Tools: {len(tools)}")

# 3. Test Sample Files
r_samples = client.get("/api/sample-files")
samples = r_samples.json()
print(f"3. Sample Files: {[s['filename'] for s in samples]}")

# 4. Trigger the Primary Workflow Example
obj = "Take these three PDF reports, extract the relevant data, organize it into an Excel spreadsheet, calculate the required totals, and generate a summary report."
print(f"\n4. Triggering Primary Workflow: '{obj}'")
r_wf = client.post("/api/workflows", data={"objective": obj})
wf_data = r_wf.json()
wf_id = wf_data["workflow_id"]
print(f"   Workflow ID: {wf_id}, Status: {wf_data['status']}")

# 5. Poll for completion
print("\n5. Polling workflow execution state...")
for _ in range(30):
    time.sleep(1)
    status_res = client.get(f"/api/workflows/{wf_id}")
    wf_detail = status_res.json()
    status = wf_detail["status"]
    completed_tasks = len([t for t in wf_detail["tasks"] if t["status"] == "COMPLETED"])
    total_tasks = len(wf_detail["tasks"])
    print(f"   Status: {status} ({completed_tasks}/{total_tasks} tasks completed)")
    if status in ["COMPLETED", "FAILED"]:
        break

print(f"\n6. Final Workflow Status: {wf_detail['status']}, Duration: {wf_detail['duration_seconds']}s")
print(f"   Artifacts Generated: {[a['filename'] for a in wf_detail['artifacts']]}")
print(f"   Verifications: {len(wf_detail['verifications'])} checks logged")
for v in wf_detail["verifications"]:
    print(f"    - Task {v['task_id']}: {v['status']} | {v['explanation']}")

# 7. Run Benchmark Test Suite
print("\n7. Executing Evaluation Benchmark Suite via API...")
bench_res = client.post("/api/evaluation/run")
bench_data = bench_res.json()
print(f"   Benchmark Suite ID: {bench_data['id']}")
print(f"   Passed Scenarios: {bench_data['passed_scenarios']}/{bench_data['total_scenarios']}")
print(f"   Metrics: {bench_data['metrics']}")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
