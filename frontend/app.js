const API_BASE = "http://127.0.0.1:8000";
const output = document.getElementById("output");

async function callApi(path, method = "POST", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) {
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(API_BASE + path, opts);
  const data = await resp.json();
  output.textContent = JSON.stringify(data, null, 2);
}

document.getElementById("btn-fgt").addEventListener("click", () => {
  callApi("/vpn/fortigate/apply");
});

document.getElementById("btn-pa").addEventListener("click", () => {
  callApi("/vpn/paloalto/apply");
});

document.getElementById("btn-test").addEventListener("click", () => {
  callApi("/vpn/test-connectivity", "POST", { dst_host: "10.20.20.1" });
});