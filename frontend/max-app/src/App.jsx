import React, { useEffect, useMemo, useState } from "react";
import { Button, Container, Grid, Panel, SearchInput, Textarea, Typography } from "@maxhub/max-ui";
import {
  getCounterparty,
  getReference,
  initAuth,
  listCounterparties,
  listTkps,
  parseRequisites,
  saveRequisites,
  submitComplex,
  submitContract,
  submitSingle,
} from "./api";

const tabs = [
  { id: "single", label: "ТКП 1 услуга" },
  { id: "complex", label: "Комплексное ТКП" },
  { id: "req", label: "Реквизиты" },
  { id: "contract", label: "Договор" },
];

function ResultBox({ data }) {
  if (!data) return null;
  const docx = data.download_docx || "";
  const pdf = data.download_pdf || "";
  return (
    <div style={{ background: "#f3f4f6", borderRadius: 8, padding: 12, marginTop: 12 }}>
      {data.error ? <div style={{ color: "#b91c1c", marginBottom: 8 }}>{data.error}</div> : null}
      {docx ? (
        <div style={{ marginBottom: 6 }}>
          <a href={docx} target="_blank" rel="noreferrer">Скачать DOCX</a>
        </div>
      ) : null}
      {pdf ? (
        <div style={{ marginBottom: 6 }}>
          <a href={pdf} target="_blank" rel="noreferrer">Скачать PDF</a>
        </div>
      ) : null}
      <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

export default function App() {
  const [status, setStatus] = useState("Инициализация...");
  const [token, setToken] = useState("");
  const [tab, setTab] = useState("single");
  const [reference, setReference] = useState(null);
  const [output, setOutput] = useState(null);
  const [cpList, setCpList] = useState([]);
  const [cpSearch, setCpSearch] = useState("");
  const [tkpSearch, setTkpSearch] = useState("");
  const [tkpList, setTkpList] = useState([]);
  const [loading, setLoading] = useState(false);

  const [single, setSingle] = useState({ date: "", service_id: "", client: "", region_id: "", s: "", srok: "", room: "", text: "" });
  const [complex, setComplex] = useState({ date: "", client: "", region_name: "", room: "", srok: "", text1: "", rows: [] });
  const [req, setReq] = useState({ name: "", inn: "", kpp: "", address: "", director: "", ogrn: "", account: "", bank: "", bik: "", kor_account: "", phone: "", email: "" });
  const [contract, setContract] = useState({ tkp_id: "", counterparty: "", date: "", price: "", payment_terms: "", include_ris: true, customer_name: "" });
  const [reqFile, setReqFile] = useState(null);

  useEffect(() => {
    initAuth()
      .then((auth) => {
        if (!auth.ok || !auth.appToken) {
          setStatus(auth.error || "Ошибка валидации");
          return null;
        }
        setToken(auth.appToken);
        setStatus("Готово");
        window.WebApp?.ready?.();
        setLoading(true);
        return getReference(auth.appToken);
      })
      .then((ref) => {
        if (ref) {
          setReference(ref);
        }
      })
      .catch(() => setStatus("Ошибка инициализации"))
      .finally(() => setLoading(false));
  }, []);

  const services = useMemo(() => reference?.services || [], [reference]);
  const regions = useMemo(() => reference?.regions || [], [reference]);
  const srokChoices = useMemo(() => reference?.srok_choices || [], [reference]);

  function updateRow(idx, key, value) {
    const rows = [...complex.rows];
    rows[idx] = { ...rows[idx], [key]: value };
    if (key === "quantity" || key === "price_per_unit") {
      const qty = Number(rows[idx].quantity || 0);
      const price = Number(rows[idx].price_per_unit || 0);
      rows[idx].total = String((qty * price).toFixed(2));
    }
    setComplex({ ...complex, rows });
  }

  async function handleSingle() {
    if (!token) return;
    setLoading(true);
    setOutput(await submitSingle(token, single));
    setLoading(false);
  }
  async function handleComplex() {
    if (!token) return;
    setLoading(true);
    setOutput(await submitComplex(token, complex));
    setLoading(false);
  }
  async function handleReqSave() {
    if (!token) return;
    setLoading(true);
    setOutput(await saveRequisites(token, req));
    setLoading(false);
  }
  async function handleContract() {
    if (!token) return;
    setLoading(true);
    setOutput(await submitContract(token, contract));
    setLoading(false);
  }
  async function handleSearch() {
    if (!token) return;
    setLoading(true);
    const data = await listCounterparties(token, cpSearch);
    setCpList(data.results || []);
    setLoading(false);
  }
  async function handleTkpSearch() {
    if (!token) return;
    setLoading(true);
    const data = await listTkps(token, tkpSearch);
    setTkpList(data.results || []);
    setLoading(false);
  }
  async function handleReqParse() {
    if (!token || !reqFile) return;
    setLoading(true);
    const parsed = await parseRequisites(token, reqFile);
    if (parsed?.fields) {
      setReq((prev) => ({ ...prev, ...parsed.fields }));
    }
    setOutput(parsed);
    setLoading(false);
  }
  async function selectCounterparty(cpId) {
    if (!token) return;
    const data = await getCounterparty(token, cpId);
    if (data?.id) {
      setContract((prev) => ({
        ...prev,
        counterparty: String(data.id),
        customer_name: data.name || prev.customer_name,
      }));
      setReq((prev) => ({ ...prev, ...data }));
    }
  }

  return (
    <Panel mode="secondary" style={{ minHeight: "100vh" }}>
      <Container style={{ padding: 12 }}>
        <Typography.Title>MAX mini app</Typography.Title>
        <Typography.Body>{status}</Typography.Body>
        {loading ? <Typography.Body>Загрузка...</Typography.Body> : null}
        <Grid cols={2} gap={8} style={{ margin: "8px 0 12px" }}>
          {tabs.map((t) => (
            <Button key={t.id} mode={tab === t.id ? "primary" : "secondary"} onClick={() => setTab(t.id)}>
              {t.label}
            </Button>
          ))}
        </Grid>

        {tab === "single" && (
          <>
            <input type="date" value={single.date} onChange={(e) => setSingle({ ...single, date: e.target.value })} />
            <select value={single.service_id} onChange={(e) => setSingle({ ...single, service_id: e.target.value })}>
              <option value="">Выберите услугу</option>
              {services.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            <input placeholder="Клиент" value={single.client} onChange={(e) => setSingle({ ...single, client: e.target.value })} />
            <select value={single.region_id} onChange={(e) => setSingle({ ...single, region_id: e.target.value })}>
              <option value="">Выберите регион</option>
              {regions.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
            <select value={single.srok} onChange={(e) => setSingle({ ...single, srok: e.target.value })}>
              <option value="">Срок разработки</option>
              {srokChoices.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
            <input placeholder="Площадь/кол-во" value={single.s} onChange={(e) => setSingle({ ...single, s: e.target.value })} />
            <input placeholder="Помещение" value={single.room} onChange={(e) => setSingle({ ...single, room: e.target.value })} />
            <Textarea placeholder="Комментарий" rows={3} value={single.text} onChange={(e) => setSingle({ ...single, text: e.target.value })} />
            <Button onClick={handleSingle}>Сформировать ТКП</Button>
          </>
        )}

        {tab === "complex" && (
          <>
            <input type="date" value={complex.date} onChange={(e) => setComplex({ ...complex, date: e.target.value })} />
            <input placeholder="Клиент" value={complex.client} onChange={(e) => setComplex({ ...complex, client: e.target.value })} />
            <input placeholder="Регион (название)" value={complex.region_name} onChange={(e) => setComplex({ ...complex, region_name: e.target.value })} />
            <input placeholder="Помещение" value={complex.room} onChange={(e) => setComplex({ ...complex, room: e.target.value })} />
            <input placeholder="Срок" value={complex.srok} onChange={(e) => setComplex({ ...complex, srok: e.target.value })} />
            <Textarea rows={3} placeholder="Текст" value={complex.text1} onChange={(e) => setComplex({ ...complex, text1: e.target.value })} />
            <Button mode="secondary" onClick={() => setComplex({ ...complex, rows: [...complex.rows, { service_name: "", comment: "", srok: "", unit: "m2", quantity: "1", price_per_unit: "0", total: "0.00" }] })}>
              Добавить позицию
            </Button>
            {complex.rows.map((row, idx) => (
              <div key={`row-${idx}`} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 8, marginBottom: 8 }}>
                <input placeholder="Услуга" value={row.service_name || ""} onChange={(e) => updateRow(idx, "service_name", e.target.value)} />
                <input placeholder="Комментарий" value={row.comment || ""} onChange={(e) => updateRow(idx, "comment", e.target.value)} />
                <input placeholder="Срок" value={row.srok || ""} onChange={(e) => updateRow(idx, "srok", e.target.value)} />
                <select value={row.unit || "m2"} onChange={(e) => updateRow(idx, "unit", e.target.value)}>
                  <option value="m2">м2</option>
                  <option value="piece">шт</option>
                </select>
                <input placeholder="Количество" value={row.quantity || ""} onChange={(e) => updateRow(idx, "quantity", e.target.value)} />
                <input placeholder="Цена за единицу" value={row.price_per_unit || ""} onChange={(e) => updateRow(idx, "price_per_unit", e.target.value)} />
                <input placeholder="Итого" value={row.total || ""} onChange={(e) => updateRow(idx, "total", e.target.value)} />
                <Button mode="secondary" onClick={() => setComplex({ ...complex, rows: complex.rows.filter((_, i) => i !== idx) })}>Удалить</Button>
              </div>
            ))}
            <Button onClick={handleComplex}>Сформировать комплексное ТКП</Button>
          </>
        )}

        {tab === "req" && (
          <>
            <input type="file" accept=".doc,.docx,.pdf" onChange={(e) => setReqFile(e.target.files?.[0] || null)} />
            <Button mode="secondary" onClick={handleReqParse} disabled={!reqFile}>Извлечь из файла</Button>
            <input placeholder="Наименование" value={req.name} onChange={(e) => setReq({ ...req, name: e.target.value })} />
            <input placeholder="ИНН" value={req.inn} onChange={(e) => setReq({ ...req, inn: e.target.value })} />
            <input placeholder="КПП" value={req.kpp} onChange={(e) => setReq({ ...req, kpp: e.target.value })} />
            <input placeholder="Адрес" value={req.address} onChange={(e) => setReq({ ...req, address: e.target.value })} />
            <input placeholder="Генеральный директор" value={req.director} onChange={(e) => setReq({ ...req, director: e.target.value })} />
            <input placeholder="ОГРН" value={req.ogrn} onChange={(e) => setReq({ ...req, ogrn: e.target.value })} />
            <input placeholder="Расчетный счет" value={req.account} onChange={(e) => setReq({ ...req, account: e.target.value })} />
            <input placeholder="Банк" value={req.bank} onChange={(e) => setReq({ ...req, bank: e.target.value })} />
            <input placeholder="БИК" value={req.bik} onChange={(e) => setReq({ ...req, bik: e.target.value })} />
            <input placeholder="Корр. счет" value={req.kor_account} onChange={(e) => setReq({ ...req, kor_account: e.target.value })} />
            <input placeholder="Телефон" value={req.phone} onChange={(e) => setReq({ ...req, phone: e.target.value })} />
            <input placeholder="Email" value={req.email} onChange={(e) => setReq({ ...req, email: e.target.value })} />
            <Button onClick={handleReqSave}>Сохранить карточку</Button>
            <SearchInput value={cpSearch} onChange={(e) => setCpSearch(e.target.value)} placeholder="Поиск контрагентов" />
            <Button mode="secondary" onClick={handleSearch}>Искать</Button>
            {cpList.map((cp) => (
              <button
                key={cp.id}
                type="button"
                onClick={() => selectCounterparty(cp.id)}
                style={{ width: "100%", textAlign: "left", padding: "8px 6px", border: "1px solid #e5e7eb", borderRadius: 8, marginBottom: 6, background: "#fff" }}
              >
                {(cp.name || "—")} / {cp.inn || "—"}
              </button>
            ))}
          </>
        )}

        {tab === "contract" && (
          <>
            <SearchInput value={tkpSearch} onChange={(e) => setTkpSearch(e.target.value)} placeholder="Поиск ТКП (номер/клиент/услуга)" />
            <Button mode="secondary" onClick={handleTkpSearch}>Найти ТКП</Button>
            {tkpList.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setContract((prev) => ({ ...prev, tkp_id: String(t.id), date: (t.date || "").slice(0, 10), price: String(t.sum_total || ""), customer_name: t.client || "" }))}
                style={{ width: "100%", textAlign: "left", padding: "8px 6px", border: "1px solid #e5e7eb", borderRadius: 8, marginBottom: 6, background: "#fff" }}
              >
                #{t.id} {t.number} | {t.client || "—"} | {t.service || "—"}
              </button>
            ))}
            <SearchInput value={cpSearch} onChange={(e) => setCpSearch(e.target.value)} placeholder="Поиск контрагента" />
            <Button mode="secondary" onClick={handleSearch}>Найти контрагента</Button>
            {cpList.map((cp) => (
              <button
                key={`c-${cp.id}`}
                type="button"
                onClick={() => setContract((prev) => ({ ...prev, counterparty: String(cp.id), customer_name: cp.name || prev.customer_name }))}
                style={{ width: "100%", textAlign: "left", padding: "8px 6px", border: "1px solid #e5e7eb", borderRadius: 8, marginBottom: 6, background: "#fff" }}
              >
                {cp.name || "—"} / {cp.inn || "—"}
              </button>
            ))}
            <input placeholder="ID ТКП" value={contract.tkp_id} onChange={(e) => setContract({ ...contract, tkp_id: e.target.value })} />
            <input placeholder="ID контрагента" value={contract.counterparty} onChange={(e) => setContract({ ...contract, counterparty: e.target.value })} />
            <input placeholder="Заказчик (customer_name)" value={contract.customer_name} onChange={(e) => setContract({ ...contract, customer_name: e.target.value })} />
            <input type="date" value={contract.date} onChange={(e) => setContract({ ...contract, date: e.target.value })} />
            <input placeholder="Цена" value={contract.price} onChange={(e) => setContract({ ...contract, price: e.target.value })} />
            <Textarea rows={3} placeholder="Условия оплаты" value={contract.payment_terms || ""} onChange={(e) => setContract({ ...contract, payment_terms: e.target.value })} />
            <label style={{ display: "flex", gap: 8, alignItems: "center", margin: "4px 0 8px" }}>
              <input
                type="checkbox"
                checked={Boolean(contract.include_ris)}
                onChange={(e) => setContract({ ...contract, include_ris: e.target.checked })}
                style={{ width: "auto", margin: 0 }}
              />
              Включить пункт про РИС
            </label>
            <Button onClick={handleContract}>Сформировать договор</Button>
          </>
        )}

        <ResultBox data={output} />
      </Container>
    </Panel>
  );
}
