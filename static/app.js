// State
let config = null;
let currentResults = [];
let currentPage = 1;
const LIMIT = 25;
let currentFilters = {};

// DOM Elements
const els = {
    apiStatus: document.getElementById('apiStatus'),
    presetGrid: document.getElementById('presetGrid'),
    procType: document.getElementById('procurementType'),
    setAside: document.getElementById('setAside'),
    btnSearch: document.getElementById('searchBtn'),
    btnClear: document.getElementById('clearFilters'),
    
    // Inputs
    title: document.getElementById('titleSearch'),
    naics: document.getElementById('naicsCode'),
    state: document.getElementById('stateFilter'),
    zip: document.getElementById('zipFilter'),
    dFrom: document.getElementById('dateFrom'),
    dTo: document.getElementById('dateTo'),
    rFrom: document.getElementById('rdlFrom'),
    rTo: document.getElementById('rdlTo'),
    
    // Views
    welcome: document.getElementById('welcomeState'),
    loading: document.getElementById('loadingState'),
    error: document.getElementById('errorState'),
    errorMsg: document.getElementById('errorMessage'),
    resultsList: document.getElementById('resultsList'),
    pagination: document.getElementById('pagination'),
    
    // Stats
    total: document.getElementById('totalResults'),
    showing: document.getElementById('showingResults'),
    activeF: document.getElementById('activeFilters'),
    btnExport: document.getElementById('exportBtn'),
    
    // Pagination
    btnPrev: document.getElementById('prevPage'),
    btnNext: document.getElementById('nextPage'),
    pageInfo: document.getElementById('pageInfo'),

    // Modal
    modalOverlay: document.getElementById('modalOverlay'),
    modalContent: document.getElementById('modalContent'),
    modalClose: document.getElementById('modalClose')
};

// Initialize
async function init() {
    try {
        const res = await fetch('/api/config');
        config = await res.json();
        
        setupApiStatus();
        populateFilters();
        setupEventListeners();
        setDefaultDates();
        
    } catch (err) {
        console.error("Failed to load config:", err);
        showError("Failed to connect to backend server. Is it running?");
    }
}

function setupApiStatus() {
    const dot = els.apiStatus.querySelector('.status-dot');
    const text = els.apiStatus.querySelector('.status-text');
    
    if (config.has_api_key) {
        dot.classList.add('active');
        text.textContent = 'API Ready';
    } else {
        dot.style.background = '#f59e0b';
        text.textContent = 'Using Demo Key';
        text.style.color = '#f59e0b';
    }
}

function setDefaultDates() {
    const today = new Date();
    const ninetyDaysAgo = new Date();
    ninetyDaysAgo.setDate(today.getDate() - 90);
    
    els.dTo.value = today.toISOString().split('T')[0];
    els.dFrom.value = ninetyDaysAgo.toISOString().split('T')[0];
}

function populateFilters() {
    // Populate Presets
    for (const [key, t] of Object.entries(config.naics_presets)) {
        const btn = document.createElement('button');
        btn.className = 'preset-btn';
        btn.innerHTML = `<strong>${t.label}</strong><br><span style="font-size:0.75rem;opacity:0.7">${t.description}</span>`;
        btn.onclick = () => selectPreset(key, btn);
        els.presetGrid.appendChild(btn);
    }
    
    // Populate Procurement Types
    for (const [val, label] of Object.entries(config.procurement_types)) {
        els.procType.add(new Option(label, val));
    }
    
    // Populate Set-Asides
    for (const [val, label] of Object.entries(config.set_aside_options)) {
        els.setAside.add(new Option(`${val} - ${label}`, val));
    }
}

function selectPreset(key, btnNode) {
    // Update UI toggle
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    if (btnNode) btnNode.classList.add('active');
    
    const preset = config.naics_presets[key];
    els.naics.value = preset.codes.join(',');
}

function setupEventListeners() {
    els.btnSearch.addEventListener('click', () => {
        currentPage = 1;
        performSearch();
    });
    
    els.btnClear.addEventListener('click', () => {
        document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
        els.title.value = '';
        els.naics.value = '';
        els.procType.value = '';
        els.setAside.value = '';
        els.state.value = '';
        els.zip.value = '';
        els.rFrom.value = '';
        els.rTo.value = '';
        setDefaultDates();
    });

    els.btnPrev.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            performSearch(true);
        }
    });

    els.btnNext.addEventListener('click', () => {
        currentPage++;
        performSearch(true);
    });

    els.modalClose.addEventListener('click', closeModal);
    els.modalOverlay.addEventListener('click', (e) => {
        if (e.target === els.modalOverlay) closeModal();
    });
}

function formatDateForApi(htmlDate) {
    if (!htmlDate) return '';
    const [y, m, d] = htmlDate.split('-');
    return `${m}/${d}/${y}`;
}

function formatDateForDisplay(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch { return dateStr; }
}

async function performSearch(isPagination = false) {
    // Hide UI elements
    els.welcome.style.display = 'none';
    els.error.style.display = 'none';
    els.resultsList.style.display = 'none';
    els.pagination.style.display = 'none';
    els.loading.style.display = 'block';

    if (!isPagination) {
        // Gather filters
        currentFilters = {
            postedFrom: formatDateForApi(els.dFrom.value),
            postedTo: formatDateForApi(els.dTo.value),
            title: els.title.value.trim(),
            ncode: els.naics.value.trim(),
            ptype: els.procType.value,
            typeOfSetAside: els.setAside.value,
            state: els.state.value.trim().toUpperCase(),
            zip: els.zip.value.trim(),
            rdlfrom: formatDateForApi(els.rFrom.value),
            rdlto: formatDateForApi(els.rTo.value),
        };
        
        // Count active visual filters
        let c = 0;
        if(currentFilters.title) c++;
        if(currentFilters.ncode) c++;
        if(currentFilters.ptype) c++;
        if(currentFilters.typeOfSetAside) c++;
        if(currentFilters.state) c++;
        els.activeF.textContent = c;
    }

    // Build URL query string
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(currentFilters)) {
        if (v) params.append(k, v);
    }
    
    const offset = (currentPage - 1) * LIMIT;
    params.append('limit', LIMIT);
    params.append('offset', offset);

    try {
        const res = await fetch(`/api/search?${params.toString()}`);
        const data = await res.json();
        
        if (!res.ok) throw new Error(data.message || data.error || 'API Request Failed');
        
        displayResults(data);
        
    } catch (err) {
        console.error("Search error:", err);
        showError(err.message);
    }
}

function displayResults(data) {
    els.loading.style.display = 'none';
    els.resultsList.innerHTML = '';
    
    currentResults = data.opportunitiesData || [];
    const total = data.totalRecords || 0;
    
    els.total.textContent = total;
    els.showing.textContent = currentResults.length;
    
    if (currentResults.length === 0) {
        els.resultsList.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-secondary);">No opportunities found matching these filters.</div>`;
        els.resultsList.style.display = 'block';
        return;
    }

    currentResults.forEach((opp, i) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.onclick = () => openModal(i);
        
        const dept = opp.department || '';
        const sub = opp.subTier ? ` • ${opp.subTier}` : '';
        const agency = `${dept}${sub}`;
        
        let badgesHtml = '';
        if (opp.active === 'Yes') badgesHtml += `<span class="badge active">Active</span>`;
        if (opp.type) badgesHtml += `<span class="badge type">${opp.type}</span>`;
        if (opp.naicsCode) badgesHtml += `<span class="badge">NAICS: ${opp.naicsCode}</span>`;
        if (opp.typeOfSetAsideDescription) badgesHtml += `<span class="badge">🎁 ${opp.typeOfSetAsideDescription}</span>`;

        card.innerHTML = `
            <div class="card-header">
                <div>
                    <h3 class="card-title">${opp.title || 'Untitled Opportunity'}</h3>
                    <div class="card-agency">${agency}</div>
                </div>
            </div>
            
            <div class="badges">${badgesHtml}</div>
            
            <div class="card-meta">
                <div class="meta-item">
                    <span class="meta-label">Notice ID / Sol. #</span>
                    <span class="meta-value mono">${opp.solicitationNumber || opp.noticeId || 'N/A'}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Posted Date</span>
                    <span class="meta-value">${formatDateForDisplay(opp.postedDate)}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Response Due</span>
                    <span class="meta-value">${formatDateForDisplay(opp.responseDeadLine)}</span>
                </div>
            </div>
        `;
        els.resultsList.appendChild(card);
    });
    
    els.resultsList.style.display = 'flex';
    
    // Pagination logic
    els.btnPrev.disabled = currentPage === 1;
    els.btnNext.disabled = currentResults.length < LIMIT || (currentPage * LIMIT) >= total;
    els.pageInfo.textContent = `Page ${currentPage} of ${Math.ceil(total/LIMIT) || 1}`;
    els.pagination.style.display = 'flex';
    
    // Scroll to top of results
    document.querySelector('.content').scrollTo(0,0);
}

function showError(msg) {
    els.loading.style.display = 'none';
    els.errorMsg.textContent = msg;
    els.error.style.display = 'flex';
}
window.retrySearch = () => performSearch(true);

function openModal(index) {
    const opp = currentResults[index];
    if (!opp) return;
    
    const uiLink = opp.uiLink && opp.uiLink !== 'null' ? opp.uiLink : `https://sam.gov/opp/${opp.noticeId}/view`;

    let contentHtml = `
        <div class="m-header">
            <div class="m-dept">${opp.department || 'N/A'} ${opp.subTier ? `> ${opp.subTier}` : ''}</div>
            <h2 class="m-title">${opp.title || 'Untitled'}</h2>
            <div class="m-sub">Solicitation Number: <span class="mono">${opp.solicitationNumber || 'N/A'}</span></div>
        </div>
        
        <div class="m-grid">
            <div class="m-detail">
                <div class="meta-label">Notice Type</div>
                <div class="meta-value">${opp.type || 'N/A'}</div>
            </div>
            <div class="m-detail">
                <div class="meta-label">Set-Aside</div>
                <div class="meta-value">${opp.typeOfSetAsideDescription || 'None'}</div>
            </div>
            <div class="m-detail">
                <div class="meta-label">NAICS Code</div>
                <div class="meta-value">${opp.naicsCode || 'N/A'}</div>
            </div>
            <div class="m-detail">
                <div class="meta-label">Classification Code</div>
                <div class="meta-value">${opp.classificationCode || 'N/A'}</div>
            </div>
            <div class="m-detail">
                <div class="meta-label">Posted Date</div>
                <div class="meta-value">${formatDateForDisplay(opp.postedDate)}</div>
            </div>
            <div class="m-detail">
                <div class="meta-label">Response Deadline</div>
                <div class="meta-value">${formatDateForDisplay(opp.responseDeadLine)}</div>
            </div>
        </div>
        
        <div class="meta-label" style="margin-bottom:8px">Primary Point of Contact</div>
        <div class="m-detail" style="margin-bottom:24px">
    `;
    
    if (opp.pointOfContact && opp.pointOfContact.length > 0) {
        const poc = opp.pointOfContact[0];
        contentHtml += `
            <div style="font-weight:600">${poc.fullName || 'N/A'} (${poc.title || 'Contact'})</div>
            <div>📧 <a href="mailto:${poc.email}" style="color:var(--accent-primary)">${poc.email || 'N/A'}</a></div>
            <div>📞 ${poc.phone || 'N/A'}</div>
        `;
    } else {
        contentHtml += `<em>No point of contact listed in API.</em>`;
    }
    
    contentHtml += `</div>
        <a href="${uiLink}" target="_blank" class="m-link">View Full Details on SAM.gov ↗</a>
    `;

    els.modalContent.innerHTML = contentHtml;
    els.modalOverlay.style.display = 'flex';
}

function closeModal() {
    els.modalOverlay.style.display = 'none';
}

// Start
document.addEventListener('DOMContentLoaded', init);
