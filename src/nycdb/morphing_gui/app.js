const pathsByRisk = [
  "M300,120 C380,80 480,140 500,230 C525,335 470,470 355,498 C250,525 135,470 103,362 C65,235 145,145 230,126 C255,120 275,128 300,120 Z",
  "M300,110 C392,64 514,126 526,242 C538,356 456,506 333,516 C230,524 119,460 86,348 C53,236 130,126 234,108 C258,104 281,123 300,110 Z",
  "M300,95 C408,47 546,132 546,264 C546,394 455,533 319,542 C199,550 84,466 62,338 C40,211 116,104 241,90 C267,87 291,116 300,95 Z",
];

const el = {
  form: document.querySelector("#analysisForm"),
  buildingId: document.querySelector("#buildingId"),
  agencyGrid: document.querySelector("#agencyGrid"),
  timeline: document.querySelector("#timelineList"),
  confidence: document.querySelector("#confidenceValue"),
  coverage: document.querySelector("#coverageValue"),
  distress: document.querySelector("#distressValue"),
  syncStatus: document.querySelector("#syncStatus"),
  morphShape: document.querySelector("#morphShape"),
  morphCaption: document.querySelector("#morphCaption"),
};

const template = document.querySelector("#agencyCardTemplate");
const cardRefs = new Map();

function updateMorphShape(riskScore) {
  const shapeIndex = riskScore < 45 ? 0 : riskScore < 68 ? 1 : 2;
  el.morphShape.setAttribute("d", pathsByRisk[shapeIndex]);
}

function pushTimeline(message) {
  const li = document.createElement("li");
  const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  li.textContent = `${timestamp} · ${message}`;
  el.timeline.prepend(li);
  while (el.timeline.children.length > 7) {
    el.timeline.removeChild(el.timeline.lastChild);
  }
}

function buildCards(agencies) {
  el.agencyGrid.innerHTML = "";
  cardRefs.clear();
  const fragment = document.createDocumentFragment();

  agencies.forEach((agency) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector("h4").textContent = agency.id;
    node.querySelector(".agency-score").textContent = "0";
    node.querySelector(".agency-signal").textContent = agency.signal;
    fragment.appendChild(node);
    cardRefs.set(agency.id, {
      scoreEl: node.querySelector(".agency-score"),
      fillEl: node.querySelector(".progress-fill"),
    });
  });

  el.agencyGrid.appendChild(fragment);
}

async function fetchAnalysis(buildingId) {
  const response = await fetch(`/api/analyze?building=${encodeURIComponent(buildingId)}`);
  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Analysis failed (${response.status}): ${err}`);
  }
  return response.json();
}

async function renderAnalysis(result) {
  const { agencies, mode, distress, risk_index: riskIndex, building } = result;
  buildCards(agencies);

  el.syncStatus.textContent = mode === "database" ? "Live DB mode" : "Simulated mode";
  el.morphCaption.textContent = `Analyzing ${building} across city agencies…`;
  pushTimeline(`Started AI analysis for ${building} (${mode})`);

  for (let i = 0; i < agencies.length; i += 1) {
    const agency = agencies[i];
    const refs = cardRefs.get(agency.id);

    await new Promise((resolve) => setTimeout(resolve, 140));

    refs.scoreEl.textContent = `${agency.score}`;
    refs.fillEl.style.width = `${agency.score}%`;

    const coverage = i + 1;
    el.coverage.textContent = `${coverage} / ${agencies.length}`;
    el.confidence.textContent = `${Math.round((coverage / agencies.length) * 100)}%`;
    pushTimeline(`${agency.id} fused (${agency.score}/100 from ${agency.source})`);
  }

  el.distress.textContent = distress;
  updateMorphShape(riskIndex);

  el.morphCaption.textContent = `AI generated a ${distress.toLowerCase()} profile with a risk index of ${riskIndex}/100 using ${mode} data fusion.`;
  pushTimeline(`Composite profile complete (risk index ${riskIndex}/100)`);
}

el.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = el.buildingId.value.trim();
  if (!value) return;

  try {
    el.syncStatus.textContent = "Syncing…";
    const result = await fetchAnalysis(value);
    await renderAnalysis(result);
  } catch (error) {
    el.syncStatus.textContent = "Error";
    el.morphCaption.textContent = error instanceof Error ? error.message : "Unknown error";
    pushTimeline("Analysis failed");
  }
});

// Pre-build initial shell state.
buildCards([
  { id: "DOB", signal: "Permits, violations, job filings" },
  { id: "HPD", signal: "Complaints, registrations, vacate activity" },
  { id: "DOF", signal: "Sales, valuations, exemptions, tax lien" },
  { id: "OATH", signal: "Hearings and enforcement outcomes" },
  { id: "DHS", signal: "Shelter pressure in nearby catchments" },
  { id: "DOHMH", signal: "Rodent and public health indicators" },
  { id: "DCP", signal: "Land use and district context" },
  { id: "OCA", signal: "Housing court patterns and filings" },
]);
