// app/static/script.js

const form = document.getElementById("form");
const fileInput = document.getElementById("file");
const editor = document.getElementById("editor");
const outputs = document.getElementById("outputs");
const pyout = document.getElementById("pyout");
const txtout = document.getElementById("txtout");
const copyPy = document.getElementById("copyPy");
const copyTxt = document.getElementById("copyTxt");

// config
window.MIN_CONF = parseFloat(document.body.dataset.minConf || "0.85");

// ---- tiny helpers ----
function h(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k === "style" && typeof v === "object") el.setAttribute("style", Object.entries(v).map(([a,b])=>`${a}:${b}`).join(";"));
    else el.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (typeof c === "string") el.appendChild(document.createTextNode(c));
    else if (c) el.appendChild(c);
  }
  return el;
}

function attachCopy(btn, el) {
  btn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(el.textContent || "");
      btn.textContent = "Copied";
      setTimeout(() => (btn.textContent = "Copy"), 1200);
    } catch {
      btn.textContent = "Failed";
      setTimeout(() => (btn.textContent = "Copy"), 1200);
    }
  });
}
attachCopy(copyPy, pyout);
attachCopy(copyTxt, txtout);

// ---------------- Multi-column UI ----------------

/**
 * Beklenen yeni API (tercih edilen):
 * {
 *   table: {
 *     headers: ["Index","Variable","Value"] | null,
 *     rows: [
 *       [ {text:"0",conf:0.99}, {text:"A",conf:0.98}, {text:"10",conf:0.99} ],
 *       ...
 *     ]
 *   },
 *   min_conf: 0.85
 * }
 *
 * Eski API (fallback):
 * { pairs: [ {col1:{text,conf}, col2:{text,conf}}, ...], min_conf }
 */
function normalizeResponse(data) {
  if (data && data.table && Array.isArray(data.table.rows)) {
    const headers = Array.isArray(data.table.headers) ? data.table.headers : null;
    const rows = data.table.rows.map(r =>
      (r || []).map(c => ({ text: String(c?.text ?? "").trim(), conf: Number(c?.conf ?? 0) }))
    );
    return { headers, rows };
  }
  // fallback: pairs -> 2 sütunlu tabloya çevir
  if (data && Array.isArray(data.pairs)) {
    const rows = data.pairs.map(p => [
      { text: String(p.col1?.text ?? "").trim(), conf: Number(p.col1?.conf ?? 0) },
      { text: String(p.col2?.text ?? "").trim(), conf: Number(p.col2?.conf ?? 0) },
    ]);
    return { headers: ["col1", "col2"], rows };
  }
  return { headers: null, rows: [] };
}

function renderTableEditor(norm) {
  const { headers, rows } = norm;
  if (!rows.length) {
    editor.innerHTML = "";
    editor.classList.remove("hidden");
    editor.appendChild(h("div", { class: "card" }, ["No rows detected"]));
    return;
  }

  const nCols = Math.max(...rows.map(r => r.length));
  const hdr = headers && headers.length === nCols ? headers.slice() : Array.from({ length: nCols }, (_, i) => `Col ${i+1}`);

  // ---- column selectors ----
  const selWrap = h("div", { style: { display:"flex", gap:"8px", alignItems:"center", marginBottom:"10px" } }, [
    h("span", { class:"muted" }, [`Choose two columns (Right → Left mapping)`]),
  ]);

  const selLeft = h("select");
  const selRight = h("select");
  for (let i = 0; i < nCols; i++) {
    selLeft.appendChild(h("option", { value: String(i) }, [hdr[i]]));
    selRight.appendChild(h("option", { value: String(i) }, [hdr[i]]));
  }
  // varsayılan: 0 ve 1
  selLeft.value = "0";
  selRight.value = nCols >= 2 ? "1" : "0";

  selWrap.appendChild(h("label", {}, [" Left: ", selLeft]));
  selWrap.appendChild(h("label", {}, [" Right: ", selRight]));
  selWrap.appendChild(h("span", { class:"muted" }, ["(Generate: Right → Left)"]));

  // ---- editable table ----
  const table = h("table");
  const thead = h("thead");
  thead.appendChild(h("tr", {}, hdr.map(name => h("th", {}, [name]))));
  const tbody = h("tbody");

  rows.forEach((r, ri) => {
    const tr = h("tr");
    for (let ci = 0; ci < nCols; ci++) {
      const cell = r[ci] || { text:"", conf:0 };
      const inp = h("input", { type:"text", value:cell.text });
      if (Number(cell.conf) < Number(window.MIN_CONF)) inp.classList.add("lowconf");
      inp.dataset.ri = String(ri);
      inp.dataset.ci = String(ci);
      tr.appendChild(h("td", {}, [inp]));
    }
    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);

  // ---- generate button ----
  const genBtn = h("button", { class:"btn", type:"button" }, ["Generate outputs"]);
  genBtn.addEventListener("click", () => {
    const edited = grabEditedTable(table, nCols, rows.length);
    const leftIdx = Number(selLeft.value);
    const rightIdx = Number(selRight.value);
    generateOutputsFromTable(edited, leftIdx, rightIdx);
  });

  const card = h("div", { class:"card" }, [
    h("div", {}, [h("span", { class:"muted" }, [`Cells below confidence ${window.MIN_CONF} are highlighted for manual fix`])]),
    selWrap,
    table,
    h("div", { style:{ marginTop:"10px" } }, [genBtn]),
  ]);

  editor.innerHTML = "";
  editor.appendChild(card);
  editor.classList.remove("hidden");
}

function grabEditedTable(table, nCols, nRows) {
  const edited = Array.from({ length: nRows }, () => Array.from({ length: nCols }, () => ({ text:"", conf:1 })));
  const inputs = table.querySelectorAll('input[type=text]');
  inputs.forEach(inp => {
    const ri = Number(inp.dataset.ri);
    const ci = Number(inp.dataset.ci);
    edited[ri][ci] = { text: (inp.value || "").trim(), conf: 1 };
  });
  return edited;
}

function generateOutputsFromTable(edited, leftIdx, rightIdx) {
  const mapping = {};
  const lines = [];

  edited.forEach(row => {
    const left = String(row[leftIdx]?.text || "").trim();
    const right = String(row[rightIdx]?.text || "").trim();
    if (!left && !right) return;
    mapping[right] = left;
    lines.push(`${right} = ${left}`);
  });

  // --- C enum çıktısı ---
  const entries = Object.entries(mapping).map(([k, v]) => `    ${k} = ${v},`);
  const cEnum = ["typedef enum {", ...entries, "} MyEnum;"].join("\n");

  pyout.textContent = cEnum;  // önceden 'pyout' olan bölüme C kodu yazılacak
  txtout.textContent = lines.join("\n");
  outputs.classList.remove("hidden");
}

// ---------------- Upload / fetch ----------------
async function uploadImage(file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/extract", { method: "POST", body: fd });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      if (err && err.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  outputs.classList.add("hidden");
  editor.classList.add("hidden");
  const f = fileInput.files[0];
  if (!f) return;

  try {
    const data = await uploadImage(f);
    const norm = normalizeResponse(data);
    renderTableEditor(norm);
  } catch (err) {
    editor.innerHTML = "";
    editor.classList.remove("hidden");
    editor.appendChild(h("div", { class: "card" }, [String(err.message || err)]));
  }
});
