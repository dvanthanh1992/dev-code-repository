"use strict";

const dom = {
    body: document.body,
    modeBadge: document.getElementById("modeBadge"),
    environmentLabel: document.getElementById("environmentLabel"),
    requestCount: document.getElementById("requestCount"),
    errorCount: document.getElementById("errorCount"),
    observedRps: document.getElementById("observedRps"),
    averageLatency: document.getElementById("averageLatency"),
    headerRedisSequence: document.getElementById("headerRedisSequence"),
    rpsSlider: document.getElementById("rpsSlider"),
    rpsSetting: document.getElementById("rpsSetting"),
    clientRate: document.getElementById("clientRate"),
    inFlightCount: document.getElementById("inFlightCount"),
    toggleButton: document.getElementById("toggleButton"),
    resetButton: document.getElementById("resetButton"),
    connectionState: document.getElementById("connectionState"),
    connectionText: document.getElementById("connectionText"),
    topologySource: document.getElementById("topologySource"),
    phaseText: document.getElementById("phaseText"),
    topology: document.getElementById("topology"),
    links: document.getElementById("links"),
    packetLayer: document.getElementById("packetLayer"),
    clientNode: document.getElementById("clientNode"),
    serviceNode: document.getElementById("serviceNode"),
    serviceTunnel: document.getElementById("serviceTunnel"),
    podZone: document.getElementById("podZone"),
    podGrid: document.getElementById("podGrid"),
    podEmpty: document.getElementById("podEmpty"),
    desiredReplicas: document.getElementById("desiredReplicas"),
    readyReplicas: document.getElementById("readyReplicas"),
    updatedReplicas: document.getElementById("updatedReplicas"),
    rolloutPhase: document.getElementById("rolloutPhase"),
    podCount: document.getElementById("podCount"),
    podReadyCount: document.getElementById("podReadyCount"),
    podTerminatingCount: document.getElementById("podTerminatingCount"),
    splitSummary: document.getElementById("splitSummary"),
    trafficSplit: document.getElementById("trafficSplit"),
    redisConnection: document.getElementById("redisConnection"),
    redisConnectionText: document.getElementById("redisConnectionText"),
    redisSequence: document.getElementById("redisSequence"),
    redisStoredEvents: document.getElementById("redisStoredEvents"),
    redisWriterPods: document.getElementById("redisWriterPods"),
    podTransitions: document.getElementById("podTransitions"),
    continuityBanner: document.getElementById("continuityBanner"),
    continuityTitle: document.getElementById("continuityTitle"),
    continuityText: document.getElementById("continuityText"),
    demoValueInput: document.getElementById("demoValueInput"),
    demoValueMeta: document.getElementById("demoValueMeta"),
    saveDemoValueButton: document.getElementById("saveDemoValueButton"),
    lastRedisWriter: document.getElementById("lastRedisWriter"),
    timelineLegend: document.getElementById("timelineLegend"),
    timeline: document.getElementById("timeline"),
    successRate: document.getElementById("successRate"),
    requestLog: document.getElementById("requestLog"),
    latestRequestStatus: document.getElementById("latestRequestStatus"),
    toastStack: document.getElementById("toastStack"),
};

const SVG_NS = "http://www.w3.org/2000/svg";

const NAMED_COLORS = {
    blue: "#388bfd",
    green: "#3fb950",
    red: "#f85149",
    yellow: "#d29922",
    orange: "#db6d28",
    purple: "#a371f7",
    pink: "#db61a2",
    cyan: "#39c5cf",
    teal: "#2dd4bf",
    indigo: "#6366f1",
};

const state = {
    config: null,
    running: true,
    configuredRps: 6,
    requests: 0,
    errors: 0,
    inFlight: 0,
    completedAt: [],
    recent: [],
    log: [],
    knownVersions: new Map(),
    latestResponseAt: 0,
    podLifecycleChanges: 0,
    pods: new Map(),
    podCards: new Map(),
    podStats: new Map(),
    removalTimers: new Map(),
    initialTopologyLoaded: false,
    topologyPolling: false,
    redisPolling: false,
    maxRedisSequence: 0,
    lastRedisSnapshotSequence: null,
    continuityBreaks: 0,
    redisConnected: false,
    activePackets: 0,
};

function hashColor(value) {
    let hash = 0;
    const text = String(value || "unknown");
    for (let index = 0; index < text.length; index += 1) {
        hash = ((hash << 5) - hash) + text.charCodeAt(index);
        hash |= 0;
    }
    return `hsl(${Math.abs(hash) % 360} 72% 58%)`;
}

function colorValue(value) {
    const raw = String(value || "").trim();
    if (!raw) return "#94a3b8";
    const named = NAMED_COLORS[raw.toLowerCase()];
    if (named) return named;
    if (/^#[0-9a-f]{3,8}$/i.test(raw)) return raw;
    if (/^(rgb|hsl)a?\(/i.test(raw)) return raw;
    return hashColor(raw);
}

function shortText(value, maxLength = 18) {
    const text = String(value || "unknown");
    return text.length <= maxLength ? text : `${text.slice(0, maxLength - 1)}…`;
}

function versionOrbText(version) {
    const text = String(version || "--").replace(/^version[-_ ]?/i, "");
    return shortText(text, 5).toUpperCase();
}

function formatNumber(value) {
    const number = Number(value || 0);
    return new Intl.NumberFormat().format(number);
}

function buildUrl(base, source) {
    const url = new URL(base, document.baseURI);
    url.searchParams.set("t", String(Date.now()));
    url.searchParams.set("source", source);
    return url.toString();
}

async function readJson(response) {
    const text = await response.text();
    if (!text) return {};
    try {
        return JSON.parse(text);
    } catch {
        throw new Error(`Invalid JSON response: ${text.slice(0, 120)}`);
    }
}

async function initialize() {
    bindEvents();

    try {
        const response = await fetch("/api/config", { cache: "no-store" });
        if (!response.ok) throw new Error(`Config HTTP ${response.status}`);
        state.config = await response.json();
    } catch (error) {
        state.config = {
            mode: "canary",
            previewUrl: "",
            trafficRps: 6,
            previewRps: 1,
            environment: "unknown",
        };
        showToast("Configuration error", String(error), "error", 9000);
    }

    state.configuredRps = Number(state.config.trafficRps || 6);
    dom.rpsSlider.value = String(state.configuredRps);
    dom.body.dataset.mode = state.config.mode === "bluegreen" ? "bluegreen" : "canary";
    dom.modeBadge.textContent = state.config.mode === "bluegreen" ? "BLUE / GREEN" : "CANARY";
    dom.environmentLabel.textContent = `environment: ${state.config.environment || "demo"}`;
    updateConfiguredRate();
    updateGlobalMetrics();

    await Promise.allSettled([pollTopology(), pollRedis()]);

    window.setInterval(() => void pollTopology(), 1000);
    window.setInterval(() => void pollRedis(), 2000);
    window.setInterval(updateObservedRps, 250);
    window.requestAnimationFrame(trafficLoop);
}

function bindEvents() {
    dom.rpsSlider.addEventListener("input", updateConfiguredRate);
    dom.toggleButton.addEventListener("click", toggleTraffic);
    dom.resetButton.addEventListener("click", resetUi);
    dom.saveDemoValueButton.addEventListener("click", () => void saveDemoValue());
    dom.demoValueInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") void saveDemoValue();
    });
    window.addEventListener("resize", () => window.requestAnimationFrame(updatePaths));
    dom.podGrid.addEventListener("scroll", () => window.requestAnimationFrame(updatePaths));
}

function updateConfiguredRate() {
    state.configuredRps = Number(dom.rpsSlider.value || 1);
    dom.rpsSetting.textContent = `${state.configuredRps} RPS`;
    dom.clientRate.textContent = `${state.configuredRps} req/s`;
}

let nextActiveAt = 0;
let nextPreviewAt = 0;

function trafficLoop(now) {
    if (state.running && state.config) {
        const activeInterval = 1000 / Math.max(1, state.configuredRps);
        if (now >= nextActiveAt && state.inFlight < 80) {
            nextActiveAt = now + activeInterval;
            void sendRequest("active");
        }

        if (state.config.mode === "bluegreen" && state.config.previewUrl) {
            const previewInterval = 1000 / Math.max(1, Number(state.config.previewRps || 1));
            if (now >= nextPreviewAt && state.inFlight < 80) {
                nextPreviewAt = now + previewInterval;
                void sendRequest("preview");
            }
        }
    }
    window.requestAnimationFrame(trafficLoop);
}

async function sendRequest(source = "active") {
    if (!state.running || !state.config) return;
    if (source === "preview" && !state.config.previewUrl) return;

    const endpoint = source === "preview" ? state.config.previewUrl : "/api/ping";
    const startedAt = performance.now();
    state.inFlight += 1;
    updateGlobalMetrics();

    let response = null;
    let data = {};
    let networkError = null;

    try {
        response = await fetch(buildUrl(endpoint, source), {
            cache: "no-store",
            headers: { Accept: "application/json" },
        });
        data = await readJson(response);
    } catch (error) {
        networkError = error;
        data = {
            request_id: "network",
            ok: false,
            version: "unreachable",
            color: "red",
            hostname: source === "preview" ? "preview-endpoint" : "active-endpoint",
            track: source,
            message: String(error),
            redis: { connected: false, sequence: null },
        };
    }

    const latency = Math.max(1, Math.round(performance.now() - startedAt));
    const ok = !networkError && Boolean(response && response.ok) && data.ok !== false;
    const result = {
        ...data,
        ok,
        latency,
        source,
        timeLabel: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false,
        }),
    };

    state.inFlight = Math.max(0, state.inFlight - 1);
    state.requests += 1;
    state.errors += ok ? 0 : 1;
    state.latestResponseAt = Date.now();
    state.completedAt.push(state.latestResponseAt);
    state.recent.push(result);
    state.recent = state.recent.slice(-100);

    ensureObservedPod(result);
    recordPodHit(result);
    recordVersion(result);
    updateRedisFromPing(result.redis);
    updateGlobalMetrics();
    renderTrafficSplit();
    appendTimeline(result);
    appendLog(result);

    window.requestAnimationFrame(() => animatePacket(result));
}

function ensureObservedPod(result) {
    const hostname = String(result.hostname || "");
    if (!hostname || hostname.endsWith("-endpoint")) return;

    const existing = state.pods.get(hostname);
    if (existing) return;

    const observedPod = {
        name: hostname,
        namespace: state.config?.podNamespace || "",
        uid: `observed-${hostname}`,
        version: result.version || "unknown",
        color: result.color || result.version || "blue",
        role: result.track || result.source || "observed",
        revision: "observed-response",
        owner: "",
        phase: "Running",
        status: "Ready",
        ready: true,
        serving: true,
        terminating: false,
        pod_ip: "",
        node: "",
        restarts: 0,
        observedOnly: true,
        deleted: false,
    };
    state.pods.set(hostname, observedPod);
    ensurePodCard(observedPod);
    sortPodCards();
    window.requestAnimationFrame(updatePaths);
}

function recordPodHit(result) {
    const hostname = String(result.hostname || "unknown");
    const current = state.podStats.get(hostname) || {
        requests: 0,
        errors: 0,
        totalLatency: 0,
        lastLatency: 0,
    };
    current.requests += 1;
    current.errors += result.ok ? 0 : 1;
    current.totalLatency += result.latency;
    current.lastLatency = result.latency;
    state.podStats.set(hostname, current);

    const pod = state.pods.get(hostname);
    if (pod) updatePodCard(pod);
}

function recordVersion(result) {
    const version = String(result.version || "unknown");
    const current = state.knownVersions.get(version) || {
        color: colorValue(result.color || version),
        count: 0,
    };
    current.count += 1;
    current.color = colorValue(result.color || version);
    state.knownVersions.set(version, current);
    renderLegend();
}

function renderLegend() {
    const ordered = Array.from(state.knownVersions.entries())
        .sort((left, right) => right[1].count - left[1].count)
        .slice(0, 6);

    dom.timelineLegend.replaceChildren();
    for (const [version, info] of ordered) {
        const chip = document.createElement("div");
        chip.className = "legend-chip";

        const dot = document.createElement("span");
        dot.className = "legend-chip-dot";
        dot.style.setProperty("--chip-color", info.color);

        const text = document.createElement("span");
        text.textContent = `${version} · ${info.count}`;

        chip.append(dot, text);
        dom.timelineLegend.appendChild(chip);
    }
}

async function pollTopology() {
    if (state.topologyPolling) return;
    state.topologyPolling = true;
    try {
        const response = await fetch(`/api/topology?t=${Date.now()}`, { cache: "no-store" });
        const data = await readJson(response);
        if (!response.ok) throw new Error(`Topology HTTP ${response.status}`);
        applyTopology(data);
    } catch (error) {
        dom.topologySource.textContent = "Discovery error";
        dom.topologySource.classList.add("fallback");
        dom.phaseText.textContent = `Pod discovery failed: ${String(error)}`;
    } finally {
        state.topologyPolling = false;
    }
}

function applyTopology(data) {
    const sourceIsKubernetes = data.source === "kubernetes-api";
    dom.topologySource.textContent = sourceIsKubernetes ? "Kubernetes API" : "Local fallback";
    dom.topologySource.classList.toggle("fallback", !sourceIsKubernetes);
    dom.topologySource.title = data.error || `${data.namespace || ""} · ${data.selector || ""}`;

    const incomingPods = Array.isArray(data.pods) ? data.pods : [];
    const currentNames = new Set();

    for (const rawPod of incomingPods) {
        const pod = {
            ...rawPod,
            name: String(rawPod.name || "unknown-pod"),
            version: String(rawPod.version || "unknown"),
            color: rawPod.color || rawPod.version || "blue",
            role: String(rawPod.role || "unclassified"),
            revision: String(rawPod.revision || "unknown"),
            status: String(rawPod.status || "Unknown"),
            ready: Boolean(rawPod.ready),
            serving: Boolean(rawPod.serving),
            terminating: Boolean(rawPod.terminating),
            deleted: false,
            observedOnly: false,
        };
        currentNames.add(pod.name);

        const previous = state.pods.get(pod.name);
        const removalTimer = state.removalTimers.get(pod.name);
        if (removalTimer) {
            window.clearTimeout(removalTimer);
            state.removalTimers.delete(pod.name);
        }

        state.pods.set(pod.name, pod);
        ensurePodCard(pod);

        if (state.initialTopologyLoaded && !previous) {
            state.podLifecycleChanges += 1;
            dom.podTransitions.textContent = formatNumber(state.podLifecycleChanges);
            showToast(
                "Pod created",
                `${pod.name} · ${pod.version} · ${pod.status}`,
                "success",
                4200,
            );
        } else if (previous && !previous.terminating && pod.terminating) {
            showToast(
                "Pod terminating",
                `${pod.name} is being removed from the rollout.`,
                "warning",
                5200,
            );
        }
    }

    for (const [name, previous] of Array.from(state.pods.entries())) {
        if (currentNames.has(name) || previous.deleted) continue;
        const deleted = {
            ...previous,
            status: "Deleted",
            ready: false,
            serving: false,
            terminating: false,
            deleted: true,
        };
        state.pods.set(name, deleted);
        updatePodCard(deleted);

        if (state.initialTopologyLoaded && !previous.observedOnly) {
            state.podLifecycleChanges += 1;
            dom.podTransitions.textContent = formatNumber(state.podLifecycleChanges);
            showToast(
                "Pod deleted",
                `${name} disappeared after rollout scale-down.`,
                "warning",
                4200,
            );
        }

        const timer = window.setTimeout(() => {
            const entry = state.podCards.get(name);
            if (entry) entry.card.remove();
            state.podCards.delete(name);
            state.pods.delete(name);
            state.removalTimers.delete(name);
            sortPodCards();
            window.requestAnimationFrame(updatePaths);
        }, 5000);
        state.removalTimers.set(name, timer);
    }

    state.initialTopologyLoaded = true;
    renderTopologySummary(data);
    sortPodCards();
    window.requestAnimationFrame(updatePaths);
}

function renderTopologySummary(data) {
    const summary = data.summary || {};
    const rollout = data.rollout || null;
    const total = Number(summary.pods || 0);
    const ready = Number(summary.ready || 0);
    const terminating = Number(summary.terminating || 0);
    const revisions = Number(summary.revisions || 0);

    dom.podCount.textContent = String(total);
    dom.podReadyCount.textContent = String(ready);
    dom.podTerminatingCount.textContent = String(terminating);

    if (rollout) {
        dom.desiredReplicas.textContent = String(rollout.desired_replicas ?? "–");
        dom.readyReplicas.textContent = String(rollout.ready_replicas ?? ready);
        dom.updatedReplicas.textContent = String(rollout.updated_replicas ?? "–");
        dom.rolloutPhase.textContent = shortText(rollout.phase || "Unknown", 10);
        dom.rolloutPhase.title = rollout.message || rollout.phase || "";
    } else {
        dom.desiredReplicas.textContent = String(total || "–");
        dom.readyReplicas.textContent = String(ready || "–");
        dom.updatedReplicas.textContent = "–";
        dom.rolloutPhase.textContent = data.available ? "Pods" : "Local";
    }

    if (terminating > 0) {
        dom.phaseText.textContent = `Rolling update: ${terminating} Pod${terminating === 1 ? "" : "s"} terminating, ${ready} Ready`;
    } else if (revisions > 1) {
        dom.phaseText.textContent = `Rollout in progress: ${revisions} revisions are running, ${ready}/${total} Ready`;
    } else if (rollout) {
        const detail = rollout.message ? ` · ${rollout.message}` : "";
        dom.phaseText.textContent = `${rollout.name}: ${rollout.phase || "Unknown"}${detail}`;
    } else if (data.error) {
        dom.phaseText.textContent = `Fallback topology · ${data.error}`;
    } else {
        dom.phaseText.textContent = `${ready}/${total} application Pods Ready`;
    }
}

function ensurePodCard(pod) {
    let entry = state.podCards.get(pod.name);
    if (!entry) {
        const card = document.createElement("article");
        card.className = "pod-card";
        card.dataset.podName = pod.name;
        card.innerHTML = `
            <div class="pod-card-top">
                <div class="pod-identity">
                    <div class="pod-version-row">
                        <div class="pod-version-orb" data-field="orb">--</div>
                        <div>
                            <div class="pod-version" data-field="version">unknown</div>
                            <div class="pod-role" data-field="role">unclassified</div>
                        </div>
                    </div>
                </div>
                <div class="pod-status" data-field="status-wrap">
                    <span class="pod-status-dot"></span>
                    <span data-field="status">Unknown</span>
                </div>
            </div>
            <div class="pod-name" data-field="name"></div>
            <div class="pod-revision" data-field="revision"></div>
            <div class="pod-card-stats">
                <div class="pod-card-stat"><span>Requests</span><strong data-field="requests">0</strong></div>
                <div class="pod-card-stat"><span>Avg latency</span><strong data-field="latency">0ms</strong></div>
                <div class="pod-card-stat"><span>Restarts</span><strong data-field="restarts">0</strong></div>
            </div>
        `;
        entry = {
            card,
            refs: {
                orb: card.querySelector('[data-field="orb"]'),
                version: card.querySelector('[data-field="version"]'),
                role: card.querySelector('[data-field="role"]'),
                status: card.querySelector('[data-field="status"]'),
                name: card.querySelector('[data-field="name"]'),
                revision: card.querySelector('[data-field="revision"]'),
                requests: card.querySelector('[data-field="requests"]'),
                latency: card.querySelector('[data-field="latency"]'),
                restarts: card.querySelector('[data-field="restarts"]'),
            },
        };
        state.podCards.set(pod.name, entry);
        dom.podGrid.appendChild(card);
    }
    updatePodCard(pod);
}

function updatePodCard(pod) {
    const entry = state.podCards.get(pod.name);
    if (!entry) return;

    const { card, refs } = entry;
    const podColor = colorValue(pod.color || pod.version);
    const stats = state.podStats.get(pod.name) || {
        requests: 0,
        errors: 0,
        totalLatency: 0,
        lastLatency: 0,
    };
    const averageLatency = stats.requests ? Math.round(stats.totalLatency / stats.requests) : 0;

    card.style.setProperty("--pod-color", podColor);
    card.classList.remove("ready", "starting", "terminating", "deleted");
    if (pod.deleted) {
        card.classList.add("deleted");
    } else if (pod.terminating) {
        card.classList.add("terminating");
    } else if (pod.ready) {
        card.classList.add("ready");
    } else {
        card.classList.add("starting");
    }

    refs.orb.textContent = versionOrbText(pod.version);
    refs.version.textContent = pod.version;
    refs.role.textContent = pod.role || "unclassified";
    refs.status.textContent = pod.status || "Unknown";
    refs.name.textContent = pod.name;
    refs.name.title = pod.name;

    const location = [shortText(pod.revision || "unknown", 15), pod.node || "unscheduled"]
        .filter(Boolean)
        .join(" · ");
    refs.revision.textContent = location;
    refs.revision.title = `${pod.revision || ""}${pod.pod_ip ? ` · ${pod.pod_ip}` : ""}`;
    refs.requests.textContent = formatNumber(stats.requests);
    refs.latency.textContent = `${averageLatency}ms`;
    refs.restarts.textContent = formatNumber(pod.restarts || 0);
    card.title = `${pod.name}\n${pod.version} · ${pod.role}\n${pod.status}`;
}

function sortPodCards() {
    const cards = Array.from(state.pods.values()).sort((left, right) => {
        const statusRank = (pod) =>
            pod.deleted ? 3 :
            pod.terminating ? 2 :
            pod.ready ? 0 : 1;

        const roleRank = (role) => {
            const value = String(role || "").toLowerCase();

            if (["stable", "active"].includes(value)) return 0;
            if (["canary", "preview"].includes(value)) return 1;

            return 2;
        };

        return statusRank(left) - statusRank(right)
            || roleRank(left.role) - roleRank(right.role)
            || String(left.version).localeCompare(String(right.version))
            || String(left.name).localeCompare(String(right.name));
    });

    // pollTopology() runs every second. Reorder only when the actual
    // Pod list/order changed; otherwise keep existing cards attached.
    const desiredNames = cards
        .map((pod) => pod.name)
        .filter((name) => state.podCards.has(name));

    const currentNames = Array.from(dom.podGrid.children)
        .filter((element) => element.classList.contains("pod-card"))
        .map((element) => element.dataset.podName);

    const orderChanged =
        desiredNames.length !== currentNames.length
        || desiredNames.some((name, index) => name !== currentNames[index]);

    if (orderChanged) {
        for (const name of desiredNames) {
            const entry = state.podCards.get(name);
            if (entry) dom.podGrid.appendChild(entry.card);
        }
    }

    dom.podEmpty.style.display = state.podCards.size ? "none" : "grid";
}

function relativePoint(element, edge = "center") {
    const containerRect = dom.topology.getBoundingClientRect();
    const rect = element.getBoundingClientRect();
    let x = rect.left - containerRect.left + rect.width / 2;
    if (edge === "left") x = rect.left - containerRect.left;
    if (edge === "right") x = rect.right - containerRect.left;
    return {
        x,
        y: rect.top - containerRect.top + rect.height / 2,
    };
}

function curvedPath(from, to) {
    const control = Math.max(45, Math.abs(to.x - from.x) * 0.42);
    return `M ${from.x} ${from.y} C ${from.x + control} ${from.y}, ${to.x - control} ${to.y}, ${to.x} ${to.y}`;
}

function addFlowPath(from, to, className, color = "") {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", curvedPath(from, to));
    path.setAttribute("class", className);
    if (color) path.style.setProperty("--path-color", color);
    dom.links.appendChild(path);
}

function updatePaths() {
    const topologyRect = dom.topology.getBoundingClientRect();
    if (!topologyRect.width || !topologyRect.height) return;

    dom.links.setAttribute("viewBox", `0 0 ${topologyRect.width} ${topologyRect.height}`);
    dom.links.replaceChildren();

    const clientOut = relativePoint(dom.clientNode, "right");
    const serviceIn = relativePoint(dom.serviceTunnel || dom.serviceNode, "left");
    const serviceOut = relativePoint(dom.serviceTunnel || dom.serviceNode, "right");
    addFlowPath(clientOut, serviceIn, "flow-line");

    const gridRect = dom.podGrid.getBoundingClientRect();
    for (const [name, entry] of state.podCards.entries()) {
        const pod = state.pods.get(name);
        if (!pod || pod.deleted) continue;
        const cardRect = entry.card.getBoundingClientRect();
        const visible = cardRect.bottom > gridRect.top && cardRect.top < gridRect.bottom;
        if (!visible) continue;

        const podIn = relativePoint(entry.card, "left");
        let className = "flow-line pod-path";
        if (!pod.ready) className += " path-not-ready";
        if (pod.terminating) className += " path-terminating";
        addFlowPath(serviceOut, podIn, className, colorValue(pod.color || pod.version));
    }
}

function animatePacket(result) {
    const entry = state.podCards.get(String(result.hostname || ""));
    if (!entry) return;

    const gridRect = dom.podGrid.getBoundingClientRect();
    const cardRect = entry.card.getBoundingClientRect();
    if (cardRect.bottom <= gridRect.top || cardRect.top >= gridRect.bottom) return;

    if (state.activePackets > 28 && state.requests % 3 !== 0) return;
    state.activePackets += 1;

    const packet = document.createElement("div");
    packet.className = `packet${result.ok ? "" : " error"}`;
    packet.style.setProperty("--packet-color", colorValue(result.color || result.version));

    if (state.configuredRps <= 8 || state.requests % 5 === 0) {
        const label = document.createElement("span");
        label.className = "packet-label";
        label.textContent = `${result.version || "?"} · ${shortText(result.hostname, 14)}`;
        packet.appendChild(label);
    }

    dom.packetLayer.appendChild(packet);

    const start = relativePoint(dom.clientNode, "right");
    const tunnelElement = dom.serviceTunnel || dom.serviceNode;
    const tunnelIn = relativePoint(tunnelElement, "left");
    const tunnelCenter = relativePoint(tunnelElement, "center");
    const tunnelOut = relativePoint(tunnelElement, "right");
    const target = relativePoint(entry.card, "left");
    const offset = 8.5;

    // Keep Pod cards stable. The moving packet visualizes each request.

    const animation = packet.animate(
        [
            {
                transform: `translate(${start.x - offset}px, ${start.y - offset}px) scale(0.65)`,
                opacity: 0,
                offset: 0,
            },
            {
                transform: `translate(${start.x - offset}px, ${start.y - offset}px) scale(1)`,
                opacity: 1,
                offset: 0.05,
            },
            {
                transform: `translate(${tunnelIn.x - offset}px, ${tunnelIn.y - offset}px) scale(1)`,
                opacity: 1,
                offset: 0.32,
            },
            {
                transform: `translate(${tunnelCenter.x - offset}px, ${tunnelCenter.y - offset}px) scale(0.88)`,
                opacity: 1,
                offset: 0.48,
            },
            {
                transform: `translate(${tunnelOut.x - offset}px, ${tunnelOut.y - offset}px) scale(1)`,
                opacity: 1,
                offset: 0.64,
            },
            {
                transform: `translate(${target.x - offset}px, ${target.y - offset}px) scale(1.08)`,
                opacity: 1,
                offset: 0.94,
            },
            {
                transform: `translate(${target.x - offset}px, ${target.y - offset}px) scale(0.3)`,
                opacity: 0,
                offset: 1,
            },
        ],
        {
            duration: 2200,
            easing: "linear",
            fill: "forwards",
        },
    );

    animation.onfinish = () => {
        packet.remove();
        state.activePackets = Math.max(0, state.activePackets - 1);
    };
    animation.oncancel = animation.onfinish;
}

function renderTrafficSplit() {
    const samples = state.recent.slice(-100);
    const versions = new Map();

    for (const item of samples) {
        const version = String(item.version || "unknown");
        const current = versions.get(version) || {
            count: 0,
            color: colorValue(item.color || version),
        };
        current.count += 1;
        current.color = colorValue(item.color || version);
        versions.set(version, current);
    }

    const ordered = Array.from(versions.entries())
        .sort((left, right) => right[1].count - left[1].count)
        .slice(0, 4);

    dom.trafficSplit.replaceChildren();
    if (!ordered.length) {
        const empty = document.createElement("div");
        empty.className = "empty-copy";
        empty.textContent = "Waiting for traffic";
        dom.trafficSplit.appendChild(empty);
        dom.splitSummary.textContent = "No responses";
        return;
    }

    const total = ordered.reduce((sum, item) => sum + item[1].count, 0);
    const summary = [];

    for (const [version, info] of ordered) {
        const percent = Math.round((info.count / total) * 100);
        summary.push(`${version} ${percent}%`);

        const row = document.createElement("div");
        row.className = "traffic-row";

        const name = document.createElement("span");
        name.className = "traffic-version";
        name.textContent = version;
        name.title = version;

        const track = document.createElement("div");
        track.className = "traffic-track";
        const fill = document.createElement("div");
        fill.className = "traffic-fill";
        fill.style.setProperty("--traffic-width", `${percent}%`);
        fill.style.setProperty("--traffic-color", info.color);
        track.appendChild(fill);

        const value = document.createElement("span");
        value.className = "traffic-percent";
        value.textContent = `${percent}%`;

        row.append(name, track, value);
        dom.trafficSplit.appendChild(row);
    }

    dom.splitSummary.textContent = summary.slice(0, 2).join(" / ");
}

function updateGlobalMetrics() {
    dom.requestCount.textContent = formatNumber(state.requests);
    dom.errorCount.textContent = formatNumber(state.errors);
    dom.inFlightCount.textContent = formatNumber(state.inFlight);

    const samples = state.recent.slice(-100);
    const average = samples.length
        ? Math.round(samples.reduce((sum, item) => sum + item.latency, 0) / samples.length)
        : 0;
    dom.averageLatency.textContent = `${average}ms`;

    const success = state.requests
        ? Math.round(((state.requests - state.errors) / state.requests) * 1000) / 10
        : 100;
    dom.successRate.textContent = `Success ${success}%`;
}

function updateObservedRps() {
    const cutoff = Date.now() - 1000;
    state.completedAt = state.completedAt.filter((timestamp) => timestamp >= cutoff);
    dom.observedRps.textContent = String(state.completedAt.length);

    const online = Date.now() - state.latestResponseAt < 3000;
    dom.connectionState.classList.toggle("online", online);
    dom.connectionState.classList.toggle("error", !online && state.requests > 0);
    dom.connectionText.textContent = online ? "Receiving Pod responses" : "Waiting for responses";
}

function appendTimeline(result) {
    const item = document.createElement("div");
    item.className = "timeline-item";
    if (result.source === "preview") item.classList.add("preview");
    if (!result.ok) item.classList.add("error");
    item.style.setProperty("--item-color", colorValue(result.color || result.version));
    item.style.setProperty("--height", `${Math.max(18, Math.min(100, 18 + result.latency / 3))}%`);
    item.title = `${result.version} · ${result.hostname} · ${result.ok ? "OK" : "ERROR"} · ${result.latency}ms`;
    dom.timeline.appendChild(item);

    while (dom.timeline.children.length > 70) {
        dom.timeline.firstElementChild.remove();
    }
}

function appendLog(result) {
    const pod = state.pods.get(String(result.hostname || ""));
    const role = pod?.role || result.track || result.source || "unknown";
    state.log.unshift({ ...result, role });
    state.log = state.log.slice(0, 8);
    dom.requestLog.replaceChildren();

    for (const row of state.log) {
        const tr = document.createElement("tr");
        const values = [
            row.timeLabel,
            row.version || "unknown",
            row.role,
            row.hostname || "network-error",
            `${row.ok ? "OK" : "ERR"} · ${row.latency}ms`,
        ];

        values.forEach((value, index) => {
            const td = document.createElement("td");
            td.textContent = value;
            td.title = String(value);
            if (index === 4) td.className = row.ok ? "status-ok" : "status-error";
            tr.appendChild(td);
        });
        dom.requestLog.appendChild(tr);
    }

    dom.latestRequestStatus.textContent = `${result.ok ? "OK" : "ERR"} · ${result.latency}ms`;
}

function updateRedisFromPing(redis) {
    if (!redis || redis.sequence === null || redis.sequence === undefined) return;
    const sequence = Number(redis.sequence || 0);
    state.maxRedisSequence = Math.max(state.maxRedisSequence, sequence);
    dom.headerRedisSequence.textContent = formatNumber(state.maxRedisSequence);
    dom.redisSequence.textContent = formatNumber(state.maxRedisSequence);
}

async function pollRedis() {
    if (state.redisPolling) return;
    state.redisPolling = true;
    try {
        const response = await fetch(`/api/redis/state?t=${Date.now()}`, { cache: "no-store" });
        const data = await readJson(response);
        applyRedisSnapshot(data);
    } catch (error) {
        applyRedisSnapshot({ connected: false, error: String(error) });
    } finally {
        state.redisPolling = false;
    }
}

function applyRedisSnapshot(data) {
    const connected = Boolean(data.connected);
    state.redisConnected = connected;
    dom.redisConnection.classList.toggle("online", connected);
    dom.redisConnection.classList.toggle("error", !connected);
    dom.redisConnectionText.textContent = connected ? "Connected" : "Unavailable";
    dom.saveDemoValueButton.disabled = !connected;

    if (!connected) {
        dom.continuityBanner.classList.remove("error");
        dom.continuityBanner.classList.add("offline");
        dom.continuityTitle.textContent = "Redis unavailable";
        dom.continuityText.textContent = data.error || "Persistent-state verification is currently unavailable.";
        return;
    }

    dom.continuityBanner.classList.remove("offline");
    const sequence = Number(data.sequence || 0);
    if (
        state.lastRedisSnapshotSequence !== null
        && sequence < state.lastRedisSnapshotSequence
    ) {
        state.continuityBreaks += 1;
    }
    state.lastRedisSnapshotSequence = sequence;
    state.maxRedisSequence = Math.max(state.maxRedisSequence, sequence);

    const stats = data.stats || {};
    const demoValue = data.demo_value || {};
    dom.headerRedisSequence.textContent = formatNumber(state.maxRedisSequence);
    dom.redisSequence.textContent = formatNumber(sequence);
    dom.redisStoredEvents.textContent = formatNumber(data.stored_events || 0);
    dom.redisWriterPods.textContent = formatNumber(data.writer_pods || 0);
    dom.podTransitions.textContent = formatNumber(state.podLifecycleChanges);
    dom.lastRedisWriter.textContent = stats.last_writer_pod
        ? `${stats.last_writer_pod} · ${stats.last_writer_version || "unknown"}`
        : "–";

    if (state.continuityBreaks > 0) {
        dom.continuityBanner.classList.add("error");
        dom.continuityTitle.textContent = `Continuity break detected (${state.continuityBreaks})`;
        dom.continuityText.textContent = "A Redis snapshot sequence decreased. Check Redis persistence or key resets.";
    } else {
        dom.continuityBanner.classList.remove("error");
        if (state.podLifecycleChanges > 0) {
            dom.continuityTitle.textContent = `State continuous across ${state.podLifecycleChanges} Pod lifecycle changes`;
            dom.continuityText.textContent = `Redis sequence remains monotonic at ${formatNumber(sequence)} while Pods are created and deleted.`;
        } else {
            dom.continuityTitle.textContent = "Redis sequence is monotonic";
            dom.continuityText.textContent = "Start a rollout; the counter and saved value remain outside application Pods.";
        }
    }

    const savedValue = String(demoValue.value || "");
    if (document.activeElement !== dom.demoValueInput && savedValue) {
        dom.demoValueInput.value = savedValue;
    }
    if (savedValue) {
        const updatedAt = Number(demoValue.updated_at_unix_ms || 0);
        const timeText = updatedAt ? new Date(updatedAt).toLocaleTimeString() : "unknown time";
        dom.demoValueMeta.textContent = `Stored by ${demoValue.writer_pod || "unknown"} (${demoValue.writer_version || "unknown"}) at ${timeText}`;
    } else {
        dom.demoValueMeta.textContent = "Save once, then roll the application.";
    }
}

async function saveDemoValue() {
    const value = dom.demoValueInput.value.trim();
    if (!value) {
        showToast("Value required", "Enter a value before saving to Redis.", "warning");
        dom.demoValueInput.focus();
        return;
    }

    dom.saveDemoValueButton.disabled = true;
    try {
        const response = await fetch("/api/redis/value", {
            method: "PUT",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ value }),
        });
        const data = await readJson(response);
        if (!response.ok || !data.connected) {
            throw new Error(data.error || `Redis HTTP ${response.status}`);
        }
        showToast(
            "Saved to Redis",
            `${value} was written by ${data.writer_pod} (${data.writer_version}).`,
            "success",
            6500,
        );
        await pollRedis();
    } catch (error) {
        showToast("Redis write failed", String(error), "error", 8000);
    } finally {
        dom.saveDemoValueButton.disabled = !state.redisConnected;
    }
}

function resetUi() {
    state.requests = 0;
    state.errors = 0;
    state.inFlight = 0;
    state.completedAt = [];
    state.recent = [];
    state.log = [];
    state.knownVersions = new Map();
    state.podStats = new Map();
    state.podLifecycleChanges = 0;

    dom.timeline.replaceChildren();
    dom.timelineLegend.replaceChildren();
    dom.requestLog.replaceChildren();
    dom.latestRequestStatus.textContent = "No traffic";
    dom.podTransitions.textContent = "0";

    for (const pod of state.pods.values()) updatePodCard(pod);
    renderTrafficSplit();
    updateGlobalMetrics();
    updateObservedRps();
    showToast("UI counters reset", "Redis data and persistent sequence were not cleared.", "success");
}

function toggleTraffic() {
    state.running = !state.running;
    dom.toggleButton.textContent = state.running ? "PAUSE" : "RESUME";
    dom.toggleButton.classList.toggle("paused", !state.running);
    dom.phaseText.textContent = state.running
        ? "Traffic generation resumed"
        : "Traffic generation paused";
}

function showToast(title, message, type = "", duration = 5200) {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`.trim();

    const heading = document.createElement("strong");
    heading.textContent = title;
    const content = document.createElement("span");
    content.textContent = message;
    toast.append(heading, content);

    dom.toastStack.appendChild(toast);
    window.setTimeout(() => toast.remove(), duration);
}

void initialize();
