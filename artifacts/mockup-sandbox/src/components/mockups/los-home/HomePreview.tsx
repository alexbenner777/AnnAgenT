import { useEffect, useState } from "react";

interface DashboardData {
  user?: { name: string };
  health?: { readiness?: number; energy?: number };
  next_appointment?: { title: string; doctor: string; date: string };
  medications_today?: { pending: number };
  finances?: { monthly_expenses?: number };
  urgent?: string[];
  birthdays_today?: string[];
}

export function HomePreview() {
  const [data, setData] = useState<DashboardData>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/dashboard")
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const now = new Date();
  const hour = now.getHours();
  const greeting = hour < 12 ? "Доброе Утро" : hour < 17 ? "Добрый День" : "Добрый Вечер";
  const weekdays = ["Воскресенье","Понедельник","Вторник","Среда","Четверг","Пятница","Суббота"];
  const months = ["Января","Февраля","Марта","Апреля","Мая","Июня","Июля","Августа","Сентября","Октября","Ноября","Декабря"];
  const dateStr = `${weekdays[now.getDay()]}, ${now.getDate()} ${months[now.getMonth()]}`;

  const readiness = data.health?.readiness ?? 82;
  const energy = data.health?.energy ?? 6;
  const name = data.user?.name ?? "Аня";
  const urgent = data.urgent ?? [];
  const birthdays = data.birthdays_today ?? [];
  const pendingMeds = data.medications_today?.pending ?? 16;
  const expenses = data.finances?.monthly_expenses ?? 140000;
  const appt = data.next_appointment;

  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif", background: "#F4F6F9", minHeight: "100vh", maxWidth: 390, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ padding: "52px 20px 16px" }}>
        <div style={{ fontSize: 15, color: "#8E8E93", fontWeight: 400 }}>{greeting}</div>
        <div style={{ fontSize: 28, fontWeight: 700, color: "#1C1C1E", letterSpacing: -0.5 }}>
          {name} 👋
        </div>
        <div style={{ fontSize: 13, color: "#8E8E93", marginTop: 2 }}>{dateStr}</div>
      </div>

      <div style={{ padding: "0 16px", display: "flex", flexDirection: "column", gap: 12 }}>
        {/* Urgent card */}
        {(urgent.length > 0 || birthdays.length > 0) && (
          <div style={{ background: "rgba(255,255,255,0.75)", backdropFilter: "blur(20px)", borderRadius: 16, padding: "14px 16px", boxShadow: "0 2px 12px rgba(0,0,0,0.06)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 18 }}>⚡</span>
              <span style={{ fontWeight: 600, fontSize: 15, color: "#1C1C1E" }}>Сейчас важно</span>
            </div>
            {urgent.map((u, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#FF9F0A", flexShrink: 0 }} />
                <span style={{ fontSize: 13, color: "#3C3C43" }}>{u}</span>
              </div>
            ))}
            {pendingMeds > 0 && urgent.length === 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#FF9F0A", flexShrink: 0 }} />
                <span style={{ fontSize: 13, color: "#3C3C43" }}>Таблетки: {pendingMeds} не приняты</span>
              </div>
            )}
            {birthdays.map((b, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#FF9F0A", flexShrink: 0 }} />
                <span style={{ fontSize: 13, color: "#3C3C43" }}>🎂 Сегодня ДР: {b}</span>
              </div>
            ))}
          </div>
        )}

        {/* Health row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {[
            { label: "Готовность", value: String(readiness), sub: null, bar: readiness, barColor: "#5B9DB8" },
            { label: "Энергия", value: String(energy), sub: "/10", bar: energy * 10, barColor: "#34C759" },
          ].map((item) => (
            <div key={item.label} style={{ background: "rgba(255,255,255,0.75)", backdropFilter: "blur(20px)", borderRadius: 16, padding: "14px 16px", boxShadow: "0 2px 12px rgba(0,0,0,0.06)" }}>
              <div style={{ fontSize: 12, color: "#8E8E93", marginBottom: 6 }}>{item.label}</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: "#1C1C1E", letterSpacing: -0.5 }}>
                {item.value}
                {item.sub && <span style={{ fontSize: 14, fontWeight: 500, color: "#8E8E93" }}>{item.sub}</span>}
              </div>
              <div style={{ marginTop: 8, height: 4, background: "#F2F2F7", borderRadius: 2, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${item.bar}%`, background: item.barColor, borderRadius: 2, transition: "width 0.5s" }} />
              </div>
            </div>
          ))}
        </div>

        {/* Next appointment */}
        {appt && (
          <div style={{ background: "rgba(255,255,255,0.75)", backdropFilter: "blur(20px)", borderRadius: 16, padding: "14px 16px", boxShadow: "0 2px 12px rgba(0,0,0,0.06)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: "rgba(91,157,184,0.12)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>🩺</div>
              <div>
                <div style={{ fontSize: 11, color: "#8E8E93", marginBottom: 2 }}>Ближайший визит</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: "#1C1C1E" }}>{appt.title}</div>
                <div style={{ fontSize: 12, color: "#8E8E93" }}>{appt.doctor} · {appt.date}</div>
              </div>
            </div>
            <div style={{ color: "#C7C7CC", fontSize: 18 }}>›</div>
          </div>
        )}

        {/* Meds */}
        <div style={{ background: "rgba(255,255,255,0.75)", backdropFilter: "blur(20px)", borderRadius: 16, padding: "14px 16px", boxShadow: "0 2px 12px rgba(0,0,0,0.06)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: "rgba(91,157,184,0.12)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>💊</div>
            <div>
              <div style={{ fontSize: 11, color: "#8E8E93", marginBottom: 2 }}>Таблетки сегодня</div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "#1C1C1E" }}>{pendingMeds} ожидают приёма</div>
            </div>
          </div>
          <div style={{ color: "#C7C7CC", fontSize: 18 }}>›</div>
        </div>

        {/* Finances */}
        <div style={{ background: "rgba(255,255,255,0.75)", backdropFilter: "blur(20px)", borderRadius: 16, padding: "14px 16px", boxShadow: "0 2px 12px rgba(0,0,0,0.06)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: "rgba(91,157,184,0.12)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>📈</div>
            <div>
              <div style={{ fontSize: 11, color: "#8E8E93", marginBottom: 2 }}>Расходы за месяц</div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "#1C1C1E" }}>
                {loading ? "…" : `${Math.round(expenses / 1000)} тыс. ₽`}
              </div>
            </div>
          </div>
          <div style={{ color: "#C7C7CC", fontSize: 18 }}>›</div>
        </div>
      </div>

      {/* Tab bar */}
      <div style={{ position: "fixed", bottom: 0, left: "50%", transform: "translateX(-50%)", width: 390, background: "rgba(255,255,255,0.85)", backdropFilter: "blur(20px)", borderTop: "1px solid rgba(0,0,0,0.08)", padding: "8px 0 20px", display: "flex", justifyContent: "space-around" }}>
        {[
          { icon: "⊞", label: "Главная", active: true },
          { icon: "♥", label: "Здоровье", active: false },
          { icon: "📅", label: "Календарь", active: false },
          { icon: "💳", label: "Финансы", active: false },
          { icon: "···", label: "Ещё", active: false },
        ].map((tab) => (
          <div key={tab.label} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
            <div style={{ width: 28, height: 28, display: "flex", alignItems: "center", justifyContent: "center", background: tab.active ? "#5B9DB8" : "transparent", borderRadius: 8, fontSize: tab.active ? 14 : 18, color: tab.active ? "#fff" : "#8E8E93" }}>
              {tab.icon}
            </div>
            <div style={{ fontSize: 10, color: tab.active ? "#5B9DB8" : "#8E8E93", fontWeight: tab.active ? 600 : 400 }}>{tab.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
