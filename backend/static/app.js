const sessionId = "web-" + Math.random().toString(36).slice(2);
const $ = (id) => document.getElementById(id);

const example = {
  soil: { ph: 6.5, organic_carbon: 0.3, moisture: 12 },
  climate: { temperature: 29, rainfall: 480, zone: "semi-arid" },
  land: { crop: "wheat", land_use: "monoculture" },
  biodiversity: { species_richness: 5, habitat_diversity: "low" },
  human_impact: { pollution: "medium", deforestation: "low" },
  location: "Semi-arid agricultural region"
};

function setExample() {
  $("message").value =
    "Biodiversity is declining on my semi-arid wheat farm. Soil organic carbon is 0.3%, rainfall is 480 mm and the farm is monoculture.";

  $("ph").value = 6.5;
  $("soc").value = 0.3;
  $("moisture").value = 12;
  $("rainfall").value = 480;
  $("temperature").value = 29;
  $("crop").value = "wheat";
  $("landUse").value = "monoculture";
  $("habitat").value = "low";
  $("pollution").value = "medium";
  $("location").value = "Semi-arid agricultural region";

  $("jsonInput").value = JSON.stringify(example, null, 2);
}

function readForm() {
  const env = {
    soil: {},
    climate: {},
    land: {},
    biodiversity: {},
    human_impact: {},
    location: $("location").value || null
  };

  [
    ["ph", "soil", "ph"],
    ["soc", "soil", "organic_carbon"],
    ["moisture", "soil", "moisture"],
    ["rainfall", "climate", "rainfall"],
    ["temperature", "climate", "temperature"]
  ].forEach(([id, section, key]) => {
    if ($(id).value !== "") {
      env[section][key] = Number($(id).value);
    }
  });

  if ($("crop").value) env.land.crop = $("crop").value;
  if ($("landUse").value) env.land.land_use = $("landUse").value;
  if ($("habitat").value)
    env.biodiversity.habitat_diversity = $("habitat").value;
  if ($("pollution").value)
    env.human_impact.pollution = $("pollution").value;

  return env;
}

function fillFromEnvironment(env) {
  const get = (section, key) => env?.[section]?.[key] ?? "";

  $("ph").value = get("soil", "ph");
  $("soc").value = get("soil", "organic_carbon");
  $("moisture").value = get("soil", "moisture");
  $("rainfall").value = get("climate", "rainfall");
  $("temperature").value = get("climate", "temperature");
  $("crop").value = get("land", "crop");
  $("landUse").value = get("land", "land_use");
  $("habitat").value = get("biodiversity", "habitat_diversity");
  $("pollution").value = get("human_impact", "pollution");
  $("location").value = env?.location || "";
}

function renderMetrics(env) {
  const items = [
    [
      "SOC",
      env?.soil?.organic_carbon !== undefined
        ? `${env.soil.organic_carbon}%`
        : "—"
    ],
    ["Rainfall", env?.climate?.rainfall ?? "—"],
    ["Land use", env?.land?.land_use || "—"],
    ["Habitat", env?.biodiversity?.habitat_diversity || "—"]
  ];

  $("metricCards").innerHTML = items
    .map(
      ([name, value]) =>
        `<div class="metric-card"><small>${name}</small><strong>${value}</strong></div>`
    )
    .join("");
}

function renderText(text) {
  return (text || "")
    .replace(/^### (.*)$/gm, "<h3>$1</h3>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n\n/g, "<br><br>")
    .replace(/\n/g, "<br>");
}

function renderRecommendations(recommendations) {
  if (!recommendations || !recommendations.length) {
    return "";
  }

  return `
    <div class="recommendations">
      ${recommendations
        .map((rec, i) => {
          let expectedImpact = "See monitoring plan";

          if (
            rec.expected_impact &&
            typeof rec.expected_impact === "object"
          ) {
            expectedImpact = Object.entries(rec.expected_impact)
              .map(([key, value]) => `${key}: ${value}`)
              .join("<br>");
          } else if (rec.expected_impact) {
            expectedImpact = rec.expected_impact;
          }

          return `
            <div class="recommendation">
              <h3>Recommendation ${i + 1}: ${
            rec.action || "Environmental action"
          }</h3>

              <p>
                <strong>Why it works:</strong>
                ${rec.why || ""}
              </p>

              <p>
                <strong>Impacted metrics:</strong>
                ${
                  Array.isArray(rec.metrics)
                    ? rec.metrics.join(", ")
                    : rec.metrics || ""
                }
              </p>

              <p>
                <strong>Expected impact:</strong>
                ${expectedImpact}
              </p>

              <p>
                <strong>Time horizon:</strong>
                ${rec.time_horizon || "Not specified"}
              </p>

              <p>
                <strong>Monitoring:</strong>
                ${rec.monitoring || "Monitor the impacted environmental metrics regularly."}
              </p>

              <p>
                <strong>Confidence:</strong>
                ${rec.confidence || "Not specified"}
              </p>

              <p>
                <strong>Evidence:</strong>
                ${rec.evidence_summary || ""}
              </p>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderResult(data) {
  fillFromEnvironment(data.environment || {});
  renderMetrics(data.environment || {});

  $("turns").textContent = `${data.conversation_turns || 0} turns`;

  if (data.status === "needs_clarification") {
    $("clarification").classList.remove("hidden");
    $("clarification").innerHTML =
      `<strong>More information needed:</strong> ${
        data.missing?.join(", ") || ""
      }.`;
  } else {
    $("clarification").classList.add("hidden");
  }

  $("report").innerHTML = renderText(data.answer);

  if (data.recommendations && data.recommendations.length) {
    $("report").innerHTML += renderRecommendations(data.recommendations);
  }

  $("reasoning").innerHTML =
    (data.reasoning || [])
      .map((x) => `<div class="reasoning-item">${x}</div>`)
      .join("") ||
    `<div class="muted">No reasoning available.</div>`;

  $("evidence").innerHTML =
    (data.retrieved_evidence || [])
      .map(
        (e) => `
          <div class="evidence">
            <div class="evidence-title">${e.title}</div>
            <div class="evidence-meta">
              ${e.source} • ${e.year || "n.d."} • retrieval similarity ${
          e.similarity ?? "—"
        }
            </div>
            ${
              e.url
                ? `<a href="${e.url}" target="_blank" rel="noopener">Open source</a>`
                : ""
            }
          </div>
        `
      )
      .join("") ||
    `<div class="muted">No matching evidence was retrieved.</div>`;
}

async function analyze(message = null, environment = null) {
  $("analyzeBtn").disabled = true;
  $("analyzeBtn").textContent = "Analyzing...";

  try {
    const r = await fetch("/api/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        session_id: sessionId,
        message: message ?? $("message").value,
        environment
      })
    });

    const data = await r.json();

    if (!r.ok) {
      throw new Error(data.detail || "Server error");
    }

    renderResult(data);
  } catch (e) {
    $("report").innerHTML =
      `<strong>Error:</strong> ${e.message}<br><br>` +
      `Make sure the server is running with <code>python run.py</code>.`;
  } finally {
    $("analyzeBtn").disabled = false;
    $("analyzeBtn").textContent = "Analyze Environment";
  }
}

$("exampleBtn").addEventListener("click", setExample);

$("analyzeBtn").addEventListener("click", () => {
  analyze($("message").value, readForm());
});

$("jsonBtn").addEventListener("click", () => {
  try {
    analyze(
      "Analyze this structured environmental profile.",
      JSON.parse($("jsonInput").value)
    );
  } catch (e) {
    $("report").innerHTML =
      `<strong>Invalid JSON:</strong> ${e.message}`;
  }
});

$("resetBtn").addEventListener("click", async () => {
  await fetch(`/api/reset/${sessionId}`, {
    method: "POST"
  });

  $("message").value = "";
  $("jsonInput").value = "";
  $("metricCards").innerHTML = "";

  $("report").innerHTML = `
    <div class="empty">
      <div class="empty-icon">🌱</div>
      <h3>Conversation reset</h3>
      <p>Enter new environmental information.</p>
    </div>
  `;

  $("reasoning").innerHTML =
    `<div class="muted">Reasoning will appear after analysis.</div>`;

  $("evidence").innerHTML =
    `<div class="muted">Retrieved sources will appear here.</div>`;

  $("turns").textContent = "0 turns";
  $("clarification").classList.add("hidden");
});

async function healthCheck() {
  try {
    const r = await fetch("/api/health");
    const d = await r.json();

    $("status").textContent =
      `● Online • ${d.knowledge_documents} knowledge documents • ${d.rag}`;
  } catch {
    $("status").textContent = "● Server unavailable";
  }
}

healthCheck();
