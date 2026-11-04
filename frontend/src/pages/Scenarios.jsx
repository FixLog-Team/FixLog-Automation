import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { EmptyState, ErrorState, LoadingState } from "../components.jsx";
import { useServerData } from "../hooks.js";
import { toRunRequest, useRunSettings } from "../settings.jsx";

export default function Scenarios() {
  const scenarios = useServerData(api.getScenarios);
  const steps = useServerData(api.getSteps);
  const { settings } = useRunSettings();
  const navigate = useNavigate();
  const [selectedId, setSelectedId] = useState("basic");
  const [isStarting, setIsStarting] = useState(false);
  const [runError, setRunError] = useState(null);

  const stepNames = Object.fromEntries((steps.data ?? []).map((s) => [s.id, s.name]));
  const selected = scenarios.data?.find((s) => s.id === selectedId);

  const startRun = async () => {
    setIsStarting(true);
    setRunError(null);
    try {
      await api.startRun(toRunRequest(selectedId, settings));
      navigate("/runs");
    } catch (e) {
      setRunError(e.message);
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <>
      <header className="page-header">
        <h1>시나리오 관리</h1>
      </header>

      {scenarios.error && <ErrorState message={scenarios.error} />}
      {scenarios.isLoading && <LoadingState />}

      <div className="two-col">
        <section className="card">
          <h2>시나리오 목록</h2>
          {scenarios.data?.length === 0 && <EmptyState>시나리오가 없습니다.</EmptyState>}
          <ul className="scenario-list">
            {scenarios.data?.map((s) => (
              <li key={s.id}>
                <label className={s.id === selectedId ? "selected" : ""}>
                  <input
                    type="radio"
                    name="scenario"
                    checked={s.id === selectedId}
                    onChange={() => setSelectedId(s.id)}
                  />
                  <span>
                    <strong>{s.name}</strong>
                    {!s.is_builtin && <span className="tag">사용자 정의</span>}
                    <small>{s.description}</small>
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </section>

        <section className="card">
          <h2>선택한 시나리오</h2>
          {selected ? (
            <>
              <p><strong>{selected.name}</strong> <code>{selected.id}</code></p>
              <ol className="step-list">
                {selected.steps.map((id, i) => <li key={`${id}-${i}`}>{stepNames[id] ?? id}</li>)}
              </ol>
              <RunSummary settings={settings} />
              {runError && <ErrorState message={runError} />}
              <div className="actions">
                <button onClick={startRun} disabled={isStarting}>
                  {isStarting ? "실행 요청 중…" : "실행"}
                </button>
                {!selected.is_builtin && (
                  <DeleteScenarioButton scenario={selected} onDeleted={() => { setSelectedId("basic"); scenarios.reload(); }} />
                )}
              </div>
            </>
          ) : (
            <EmptyState>시나리오를 선택하세요.</EmptyState>
          )}
        </section>
      </div>

      {steps.data && <CustomScenarioForm steps={steps.data} onCreated={(s) => { scenarios.reload(); setSelectedId(s.id); }} />}
    </>
  );
}

const HEADLESS_LABEL = { "": "", true: "(headless)", false: "(headed)" };

function RunSummary({ settings }) {
  return (
    <p className="muted">
      실행 {settings.run_count}회 · 동시 {settings.concurrency} · 간격 {settings.interval_sec}초 · 단계 대기{" "}
      {settings.step_delay_ms}ms · 제한 {settings.timeout_sec}초 · 브라우저 {settings.browser_type || ".env 기본"}{" "}
      {HEADLESS_LABEL[settings.headless]}{" "}
      <Link to="/settings">설정 변경</Link>
    </p>
  );
}

function DeleteScenarioButton({ scenario, onDeleted }) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState(null);

  const remove = async () => {
    setIsDeleting(true);
    try {
      await api.deleteScenario(scenario.id);
      onDeleted();
    } catch (e) {
      setError(e.message);
    } finally {
      setIsDeleting(false);
      setIsConfirming(false);
    }
  };

  if (!isConfirming) {
    return <button className="secondary" onClick={() => setIsConfirming(true)}>삭제</button>;
  }
  return (
    <span className="confirm">
      '{scenario.name}'을(를) 삭제할까요?
      <button className="danger" onClick={remove} disabled={isDeleting}>{isDeleting ? "삭제 중…" : "삭제"}</button>
      <button className="secondary" onClick={() => setIsConfirming(false)}>취소</button>
      {error && <ErrorState message={error} />}
    </span>
  );
}

function CustomScenarioForm({ steps, onCreated }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [picked, setPicked] = useState([]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  const save = async (event) => {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      const created = await api.createScenario({ name, description, steps: picked });
      setName("");
      setDescription("");
      setPicked([]);
      onCreated(created);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsSaving(false);
    }
  };

  const canSave = name.trim() && picked.length > 0 && !isSaving;
  return (
    <section className="card">
      <h2>사용자 정의 시나리오 만들기</h2>
      <p className="muted">단계를 누른 순서대로 실행됩니다. 같은 단계를 여러 번 넣을 수 있습니다.</p>
      <form onSubmit={save} className="form-grid">
        <label>이름<input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} /></label>
        <label>설명<input value={description} onChange={(e) => setDescription(e.target.value)} maxLength={300} /></label>
        <div className="step-picker">
          {steps.map((s) => (
            <button type="button" className="chip" key={s.id} title={s.description}
              onClick={() => setPicked([...picked, s.id])}>
              + {s.name}
            </button>
          ))}
        </div>
        <div>
          선택한 단계:{" "}
          {picked.length === 0 ? <span className="muted">없음</span> : picked.map((id, i) => (
            <button type="button" className="chip chip-picked" key={`${id}-${i}`} title="눌러서 빼기"
              onClick={() => setPicked(picked.filter((_, j) => j !== i))}>
              {i + 1}. {steps.find((s) => s.id === id)?.name} ×
            </button>
          ))}
        </div>
        {error && <ErrorState message={error} />}
        <div><button type="submit" disabled={!canSave}>{isSaving ? "저장 중…" : "시나리오 저장"}</button></div>
      </form>
    </section>
  );
}
