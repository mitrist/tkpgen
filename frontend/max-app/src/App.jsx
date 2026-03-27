import React, { useEffect, useMemo, useState } from "react";
import { Button, Container, Grid, Panel, SearchInput, Textarea, Typography } from "@maxhub/max-ui";
import { getReference, initAuth, listCounterparties, saveRequisites, submitComplex, submitContract, submitSingle } from "./api";

const tabs = [
  { id: "single", label: "ТКП 1 услуга" },
  { id: "complex", label: "Комплексное ТКП" },
  { id: "req", label: "Реквизиты" },
  { id: "contract", label: "Договор" },
];

function JsonBox({ data }) {
  if (!data) return null;
  return (
    <pre style={{ background: "#f3f4f6", borderRadius: 8, padding: 12, whiteSpace: "pre-wrap" }}>
      {JSON.stringify(data, null, 2)}
    </pre>
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

  const [single, setSingle] = useState({ date: "", service_id: "", client: "", region_id: "", s: "", srok: "", room: "", text: "" });
  const [complex, setComplex] = useState({ date: "", client: "", region_name: "", room: "", srok: "", text1: "", rows: [] });
  const [req, setReq] = useState({ name: "", inn: "", kpp: "", address: "", director: "", ogrn: "", account: "", bank: "", bik: "", kor_account: "", phone: "", email: "" });
  const [contract, setContract] = useState({ tkp_id: "", counterparty: "", date: "", price: "", payment_terms: "", include_ris: true });

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
        return getReference(auth.appToken);
      })
      .then((ref) => ref && setReference(ref))
      .catch(() => setStatus("Ошибка инициализации"));
  }, []);

  const services = useMemo(() => reference?.services || [], [reference]);

  async function handleSingle() {
    setOutput(await submitSingle(token, single));
  }
  async function handleComplex() {
    setOutput(await submitComplex(token, complex));
  }
  async function handleReqSave() {
    setOutput(await saveRequisites(token, req));
  }
  async function handleContract() {
    setOutput(await submitContract(token, contract));
  }
  async function handleSearch() {
    const data = await listCounterparties(token, cpSearch);
    setCpList(data.results || []);
  }

  return (
    <Panel mode="secondary" style={{ minHeight: "100vh" }}>
      <Container style={{ padding: 12 }}>
        <Typography.Title>MAX mini app</Typography.Title>
        <Typography.Body>{status}</Typography.Body>
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
            <input placeholder="Region ID" value={single.region_id} onChange={(e) => setSingle({ ...single, region_id: e.target.value })} />
            <input placeholder="Площадь/кол-во" value={single.s} onChange={(e) => setSingle({ ...single, s: e.target.value })} />
            <Button onClick={handleSingle}>Сформировать ТКП</Button>
          </>
        )}

        {tab === "complex" && (
          <>
            <input type="date" value={complex.date} onChange={(e) => setComplex({ ...complex, date: e.target.value })} />
            <input placeholder="Клиент" value={complex.client} onChange={(e) => setComplex({ ...complex, client: e.target.value })} />
            <Textarea
              rows={4}
              value={JSON.stringify(complex.rows)}
              onChange={(e) => {
                try {
                  setComplex({ ...complex, rows: JSON.parse(e.target.value) });
                } catch {
                  // ignore while typing
                }
              }}
            />
            <Button onClick={handleComplex}>Сформировать комплексное ТКП</Button>
          </>
        )}

        {tab === "req" && (
          <>
            <input placeholder="Наименование" value={req.name} onChange={(e) => setReq({ ...req, name: e.target.value })} />
            <input placeholder="ИНН" value={req.inn} onChange={(e) => setReq({ ...req, inn: e.target.value })} />
            <Button onClick={handleReqSave}>Сохранить карточку</Button>
            <SearchInput value={cpSearch} onChange={(e) => setCpSearch(e.target.value)} placeholder="Поиск контрагентов" />
            <Button mode="secondary" onClick={handleSearch}>Искать</Button>
            {cpList.map((cp) => (
              <div key={cp.id} style={{ padding: "6px 0", borderBottom: "1px solid #ddd" }}>
                {cp.name || "—"} / {cp.inn || "—"}
              </div>
            ))}
          </>
        )}

        {tab === "contract" && (
          <>
            <input placeholder="ID ТКП" value={contract.tkp_id} onChange={(e) => setContract({ ...contract, tkp_id: e.target.value })} />
            <input placeholder="ID контрагента" value={contract.counterparty} onChange={(e) => setContract({ ...contract, counterparty: e.target.value })} />
            <input type="date" value={contract.date} onChange={(e) => setContract({ ...contract, date: e.target.value })} />
            <input placeholder="Цена" value={contract.price} onChange={(e) => setContract({ ...contract, price: e.target.value })} />
            <Button onClick={handleContract}>Сформировать договор</Button>
          </>
        )}

        <JsonBox data={output} />
      </Container>
    </Panel>
  );
}
