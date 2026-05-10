let config = null;
let currentResults = [];
let currentPage = 1;
const LIMIT = 25;
let currentFilters = {};
let currentMode = 'active';

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
    btnBulkScan: document.getElementById('bulkScanBtn'),
    
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

let activePresetKey = null;

function selectPreset(key, btnNode) {
    // Update UI toggle
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    if (btnNode) btnNode.classList.add('active');
    
    const preset = config.naics_presets[key];
    els.naics.value = preset.codes.join(',');
    activePresetKey = key;

    // Show/hide bond filter for construction
    const bondSection = document.getElementById('bondFilterSection');
    if (key === 'construction_repairs') {
        bondSection.style.display = 'flex';
    } else {
        bondSection.style.display = 'none';
        // Reset bond filter when switching away
        document.getElementById('bondAll').checked = true;
    }
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
        activePresetKey = null;
        // Hide bond filter and reset
        document.getElementById('bondFilterSection').style.display = 'none';
        document.getElementById('bondAll').checked = true;
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
    
    document.getElementById('settingsBtn').addEventListener('click', () => {
        els.modalContent.innerHTML = `
            <div class="m-header">
                <h2 class="m-title">⚙️ Configuration & Settings</h2>
            </div>
            <div class="m-grid" style="grid-template-columns: 1fr;">
                <div class="m-detail">
                    <div class="meta-label">API Status</div>
                    <div class="meta-value" style="display:flex;align-items:center;gap:8px; margin-top:8px;">
                        <span style="width:10px;height:10px;display:inline-block;border-radius:50%;background:${config.has_api_key ? '#10b981' : '#f59e0b'};"></span>
                        ${config.has_api_key ? 'API Key Loaded and Ready' : 'Using Demo Key (Limited Access)'}
                    </div>
                </div>
                <div class="m-detail">
                    <div class="meta-label">How to add a SAM.gov API Key</div>
                    <div class="meta-value" style="font-size:0.9rem; color:var(--text-secondary); margin-top:12px; line-height: 1.6;">
                        1. Log in to <a href="https://sam.gov" target="_blank" style="color:var(--accent-primary)">SAM.gov</a><br>
                        2. Navigate to your <strong>Account Details</strong> profile page.<br>
                        3. Scroll down to <strong>Public API Key</strong> and generate a new key.<br>
                        4. Open the <code>.env</code> file inside the Scrappergov folder on your desktop.<br>
                        5. Replace <code>DEMO_KEY</code> with your actual key and save the file.<br>
                    </div>
                </div>
            </div>
        `;
        els.modalOverlay.style.display = 'flex';
    });
    
    els.btnExport.addEventListener('click', async () => {
        if (!currentResults.length) return;
        els.btnExport.disabled = true;
        els.btnExport.innerHTML = `<span class="loader-ring" style="width:14px;height:14px;border-width:2px;position:relative;display:inline-block"></span> Saving...`;
        
        try {
            const res = await fetch('/api/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ results: currentResults })
            });
            const data = await res.json();
            if(!res.ok) throw new Error(data.message || data.error);
            
            els.btnExport.innerHTML = `✅ Saved!`;
            setTimeout(() => {
                 els.btnExport.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Export CSV`;
                 els.btnExport.disabled = false;
            }, 3000);
        } catch(e) {
            alert('Failed to save: ' + e.message);
            els.btnExport.innerHTML = `Export CSV`;
            els.btnExport.disabled = false;
        }
    });

    els.btnBulkScan.addEventListener('click', async () => {
        if (!currentResults.length || currentMode === 'past') return;
        
        els.btnBulkScan.disabled = true;
        els.btnBulkScan.innerHTML = `<span class="loader-ring" style="width:14px;height:14px;border-width:2px;position:relative;display:inline-block;border-color:var(--text-primary) transparent transparent transparent"></span> Scanning...`;
        
        try {
            const oppsToScan = currentResults.slice(0, 10).map(o => ({
                noticeId: o.noticeId || o.solicitationNumber,
                title: o.title
            }));
            
            const res = await fetch('/api/bulk_scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ opportunities: oppsToScan })
            });
            const data = await res.json();
            if(!res.ok) throw new Error(data.message || data.error);
            
            els.btnBulkScan.innerHTML = `✨ AI Bulk Scan (Top 10)`;
            els.btnBulkScan.disabled = false;
            
            // Apply results to cards
            if(data.data && data.data.length > 0) {
                data.data.forEach(result => {
                    // Find the card
                    const idx = currentResults.findIndex(o => (o.noticeId || o.solicitationNumber) === result.noticeId);
                    if(idx !== -1) {
                        const card = els.resultsList.children[idx];
                        if (card) {
                            let color = 'var(--accent-primary)';
                            if (result.difficulty === 'Medium') color = '#f59e0b';
                            if (result.difficulty === 'Hard') color = '#ff6b6b';
                            
                            const badgeHtml = `<div style="margin-top:12px; padding:8px; border-radius:4px; background:rgba(0,0,0,0.2); border-left: 3px solid ${color};">
                                <strong style="color:${color}">${result.difficulty} (${result.score}/100)</strong> - ${result.reason}
                            </div>`;
                            card.innerHTML += badgeHtml;
                        }
                    }
                });
            }
            
        } catch(e) {
            alert('Bulk Scan failed: ' + e.message);
            els.btnBulkScan.innerHTML = `✨ AI Bulk Scan (Top 10)`;
            els.btnBulkScan.disabled = false;
        }
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

    currentMode = document.querySelector('input[name="searchMode"]:checked').value;

    if (!isPagination) {
        // Gather filters
        const bondVal = document.querySelector('input[name="bondFilter"]:checked')?.value || 'all';
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
            bondFilter: activePresetKey === 'construction_repairs' ? bondVal : '',
        };
        
        // Low Hanging Fruit Override
        if (currentMode === 'lowHanging') {
            const today = new Date();
            const past180 = new Date();
            past180.setDate(today.getDate() - 180);
            
            const past30 = new Date();
            past30.setDate(today.getDate() - 30);
            
            const past350 = new Date();
            past350.setDate(today.getDate() - 350);
            
            currentFilters.rdlfrom = formatDateForApi(past180.toISOString().split('T')[0]);
            currentFilters.rdlto = formatDateForApi(past30.toISOString().split('T')[0]);
            
            // Required by SAM.gov API: posted dates are mandatory
            currentFilters.postedFrom = formatDateForApi(past350.toISOString().split('T')[0]);
            currentFilters.postedTo = formatDateForApi(today.toISOString().split('T')[0]);
        }
        
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

    const apiUrl = currentMode === 'past' ? `/api/awards?${params.toString()}` : `/api/search?${params.toString()}`;

    try {
        const res = await fetch(apiUrl);
        const data = await res.json();
        
        if (!res.ok) throw new Error(data.message || data.error || 'API Request Failed');
        
        displayResults(data, currentMode);
        
    } catch (err) {
        console.error("Search error:", err);
        showError(err.message);
    }
}

function displayResults(data, mode) {
    els.loading.style.display = 'none';
    els.resultsList.innerHTML = '';
    
    currentResults = mode === 'past' ? (data.awardSummary || []) : (data.opportunitiesData || []);
    const total = data.totalRecords || 0;
    
    els.total.textContent = total;
    els.showing.textContent = currentResults.length;
    
    if (currentResults.length === 0) {
        els.resultsList.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-secondary);">No results found matching these filters.</div>`;
        els.resultsList.style.display = 'block';
        els.btnExport.disabled = true;
        els.btnBulkScan.style.display = 'none';
        return;
    }
    
    els.btnExport.disabled = false;
    els.btnBulkScan.style.display = mode === 'past' ? 'none' : 'flex';

    currentResults.forEach((item, i) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.onclick = () => openModal(i, mode);

        if (mode === 'past') {
            const awData = item.awardDetails?.awardeeData || {};
            const awardeeName = awData?.awardeeHeader?.awardeeName || awData?.awardeeHeader?.legalBusinessName || 'Unknown Awardee';
            const piid = item.contractId?.piid || 'N/A';
            const agency = item.coreData?.fundingSubtierName || item.coreData?.contractingDepartmentName || 'Federal Agency';
            const dollars = item.awardDetails?.dollars?.actionObligation || item.awardDetails?.dollars?.totalContractDollars || 0;
            const dateSigned = item.awardDetails?.dates?.dateSigned || item.coreData?.dateSigned;
            
            card.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3 class="card-title">${awardeeName}</h3>
                        <div class="card-agency">${agency}</div>
                    </div>
                </div>
                
                <div class="badges">
                    <span class="badge award">Past Award</span>
                    <span class="badge">PIID: ${piid}</span>
                </div>
                
                <div class="card-meta">
                    <div class="meta-item">
                        <span class="meta-label">Date Signed</span>
                        <span class="meta-value">${formatDateForDisplay(dateSigned)}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Obligated Amount</span>
                        <span class="meta-value">$${parseFloat(dollars).toLocaleString()}</span>
                    </div>
                </div>
            `;
        } else {
            const opp = item;
            const dept = opp.department || '';
            const sub = opp.subTier ? ` • ${opp.subTier}` : '';
            const agency = `${dept}${sub}`;
            
            let badgesHtml = '';
            if (opp.active === 'Yes') badgesHtml += `<span class="badge active">Active</span>`;
            if (opp.type) badgesHtml += `<span class="badge type">${opp.type}</span>`;
            if (opp.naicsCode) badgesHtml += `<span class="badge">NAICS: ${opp.naicsCode}</span>`;
            if (opp.typeOfSetAsideDescription) badgesHtml += `<span class="badge">🎁 ${opp.typeOfSetAsideDescription}</span>`;
            if (opp._bondStatus === 'required') badgesHtml += `<span class="badge bond-required">🔒 Bond Required</span>`;
            else if (opp._bondStatus === 'none') badgesHtml += `<span class="badge bond-none">✅ No Bond</span>`;

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
        }
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

function openModal(index, mode) {
    const item = currentResults[index];
    if (!item) return;

    let contentHtml = '';

    if (mode === 'past') {
        const awData = item.awardDetails?.awardeeData || {};
        const awardeeName = awData?.awardeeHeader?.awardeeName || awData?.awardeeHeader?.legalBusinessName || 'Unknown Awardee';
        const piid = item.contractId?.piid || 'N/A';
        const agency = item.coreData?.federalOrganization?.contractingInformation?.contractingOffice?.name || item.coreData?.fundingSubtierName || 'Federal Agency';
        const dateSigned = item.awardDetails?.dates?.dateSigned || item.coreData?.dateSigned;
        const dollars = item.awardDetails?.dollars?.actionObligation || item.awardDetails?.dollars?.totalContractDollars || 0;
        const uiLink = `https://sam.gov/search/?index=cdo&keywords=${encodeURIComponent(piid)}`;

        contentHtml = `
            <div class="m-header">
                <div class="m-dept">${agency}</div>
                <h2 class="m-title">${awardeeName}</h2>
                <div class="m-sub">PIID: <span class="mono">${piid}</span></div>
            </div>
            
            <div class="m-grid">
                <div class="m-detail">
                    <div class="meta-label">Awardee UEI</div>
                    <div class="meta-value mono">${awData?.awardeeUEIInformation?.uniqueEntityId || 'N/A'}</div>
                </div>
                <div class="m-detail">
                    <div class="meta-label">Cage Code</div>
                    <div class="meta-value mono">${awData?.awardeeUEIInformation?.cageCode || 'N/A'}</div>
                </div>
                <div class="m-detail">
                    <div class="meta-label">Date Signed</div>
                    <div class="meta-value">${formatDateForDisplay(dateSigned)}</div>
                </div>
                <div class="m-detail">
                    <div class="meta-label">Obligated Amount</div>
                    <div class="meta-value">$${parseFloat(dollars).toLocaleString()}</div>
                </div>
                <div class="m-detail" style="grid-column: span 2;">
                    <div class="meta-label">Address</div>
                    <div class="meta-value">${awData?.awardeeLocation?.streetAddress1 || ''} ${awData?.awardeeLocation?.city || ''}, ${awData?.awardeeLocation?.state?.code || ''}</div>
                </div>
            </div>
            <a href="${uiLink}" target="_blank" class="m-link">View Full Details on SAM.gov ↗</a>
        `;
    } else {
        const opp = item;
        const uiLink = opp.uiLink && opp.uiLink !== 'null' ? opp.uiLink : `https://sam.gov/opp/${opp.noticeId}/view`;

        contentHtml = `
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
            <div style="margin-bottom: 24px; display: flex; flex-direction: column; gap: 12px;">
                <button class="btn btn-primary" id="generateAidBtn" style="border: 1px solid var(--accent-primary);">
                    ✨ AI: Generate Difficulty Report & Proposal
                </button>
                <div id="aiIntelligenceBox" style="display:none; background:rgba(0,0,0,0.2); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:16px;">
                    <div style="display:flex; justify-content:center; align-items:center;" id="aiLoader">
                        <div class="loader-ring" style="width:24px; height:24px; border-width:2px; margin-right: 8px; border-color: var(--accent-primary) transparent transparent transparent;"></div>
                        Loading AI Intelligence...
                    </div>
                    <div id="aiContent" style="display:none;"></div>
                </div>

                <button class="btn btn-secondary" id="sourcePartsBtn" style="border: 1px solid var(--text-muted);">
                    🛒 Auto-Source Parts
                </button>
                <div id="sourcePartsBox" style="display:none; background:rgba(0,0,0,0.2); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:16px;">
                    <div style="display:flex; justify-content:center; align-items:center;" id="sourceLoader">
                        <div class="loader-ring" style="width:24px; height:24px; border-width:2px; margin-right: 8px; border-color: var(--text-primary) transparent transparent transparent;"></div>
                        Scanning Commercial Suppliers...
                    </div>
                    <div id="sourceContent" style="display:none;"></div>
                </div>

                <button class="btn btn-secondary" id="findVendorsBtn" style="border: 1px solid #818cf8;">
                    🏢 Find Qualified Vendors in State
                </button>
                <div id="vendorFinderBox" style="display:none; background:rgba(0,0,0,0.2); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:16px;">
                    <div style="display:flex; justify-content:center; align-items:center;" id="vendorLoader">
                        <div class="loader-ring" style="width:24px; height:24px; border-width:2px; margin-right: 8px; border-color: #818cf8 transparent transparent transparent;"></div>
                        Searching for qualified vendors...
                    </div>
                    <div id="vendorContent" style="display:none;"></div>
                </div>
            </div>
            <a href="${uiLink}" target="_blank" class="m-link">View Full Details on SAM.gov ↗</a>
        `;
    }

    els.modalContent.innerHTML = contentHtml;
    
    const aiBtn = document.getElementById('generateAidBtn');
    if (aiBtn && mode !== 'past') {
        const oppCopy = item;
        aiBtn.addEventListener('click', () => window.generateIntelligence(oppCopy.noticeId, oppCopy.title));
    }
    
    const sourceBtn = document.getElementById('sourcePartsBtn');
    if (sourceBtn && mode !== 'past') {
        const oppCopy = item;
        sourceBtn.addEventListener('click', () => window.sourceParts(oppCopy.title, oppCopy.description || ''));
    }

    const vendorBtn = document.getElementById('findVendorsBtn');
    if (vendorBtn && mode !== 'past') {
        const oppCopy = item;
        const contractState = oppCopy.placeOfPerformance?.state?.code || oppCopy.officeAddress?.state || els.state.value.trim().toUpperCase() || '';
        vendorBtn.addEventListener('click', () => window.findVendors(oppCopy.noticeId, oppCopy.title, contractState, oppCopy.naicsCode || ''));
    }

    els.modalOverlay.style.display = 'flex';
}

window.generateIntelligence = async (noticeId, title) => {
    const btn = document.getElementById('generateAidBtn');
    const box = document.getElementById('aiIntelligenceBox');
    const loader = document.getElementById('aiLoader');
    const content = document.getElementById('aiContent');
    
    btn.style.display = 'none';
    box.style.display = 'block';
    loader.style.display = 'flex';
    content.style.display = 'none';
    
    try {
        const response = await fetch('/api/intelligence', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({noticeId, title})
        });
        const result = await response.json();
        
        if (!response.ok) throw new Error(result.error || result.message);
        
        loader.style.display = 'none';
        content.style.display = 'block';
        
        const d = result.data;
        const missingReqs = Array.isArray(d.missing_requirements) ? d.missing_requirements.join(', ') : d.missing_requirements;
        
        const pdfStatus = (d.pdfs_analyzed !== undefined && d.pdfs_analyzed > 0)
            ? `<div style="font-size: 0.85em; color: #4cd137; margin-bottom: 12px; padding: 8px; background: rgba(76, 209, 55, 0.1); border-radius: 4px; border-left: 3px solid #4cd137;">📄 <strong>Deep Scan:</strong> Successfully read and analyzed ${d.pdfs_analyzed} attached PDF document(s).</div>`
            : `<div style="font-size: 0.85em; color: var(--text-muted); margin-bottom: 12px; padding: 8px; background: rgba(255, 255, 255, 0.05); border-radius: 4px; border-left: 3px solid var(--text-muted);">📄 <strong>Standard Scan:</strong> No readable PDF attachments found. Analysis based on standard summary text.</div>`;

        content.innerHTML = `
            ${pdfStatus}
            <div style="margin-bottom: 16px;">
                <h3 style="margin-bottom: 8px; color: var(--accent-primary);">Difficulty Score: ${d.difficulty_score}/100</h3>
                <p style="margin-bottom:4px;"><strong>ETA:</strong> ${d.eta_weeks}</p>
                <p style="margin-bottom:4px;"><strong>Missing Requirements:</strong> ${missingReqs || 'None stated'}</p>
                <p style="margin-bottom:4px; font-size:0.9em; opacity:0.8;"><strong>Notes:</strong> ${d.notes}</p>
            </div>
            <hr style="border-color: rgba(255,255,255,0.1); margin: 16px 0;">
            <div>
                <h3 style="margin-bottom: 8px;">Proposal Template</h3>
                <div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 4px; white-space: pre-wrap; font-family: 'JetBrains Mono', monospace; font-size: 0.9em; max-height: 350px; overflow-y: auto;">${(d.proposal_template || '').replace(/</g, "&lt;").replace(/>/g, "&gt;")}</div>
                <p style="font-size: 0.8em; color: var(--accent-primary); margin-top: 12px;">✅ Saved locally to: ${result.file_saved}</p>
            </div>
        `;
        
    } catch (e) {
        loader.style.display = 'none';
        content.style.display = 'block';
        content.innerHTML = `<div style="color:#ff6b6b; padding:12px; background:rgba(255,0,0,0.1); border-radius:4px;">Error: ${e.message}</div>`;
        btn.style.display = 'block';
        btn.textContent = 'Retry Intelligence Generation';
    }
}

window.sourceParts = async (title, description) => {
    const btn = document.getElementById('sourcePartsBtn');
    const box = document.getElementById('sourcePartsBox');
    const loader = document.getElementById('sourceLoader');
    const content = document.getElementById('sourceContent');
    
    btn.style.display = 'none';
    box.style.display = 'block';
    loader.style.display = 'flex';
    content.style.display = 'none';
    
    try {
        const response = await fetch('/api/source_parts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title, description})
        });
        const result = await response.json();
        
        if (!response.ok) throw new Error(result.error || result.message);
        
        loader.style.display = 'none';
        content.style.display = 'block';
        
        const part = result.part_details;
        if (!part.has_specific_part) {
            content.innerHTML = `<div style="color:var(--text-muted); text-align:center;">No specific physical part found to source.</div>`;
            return;
        }
        
        let html = `
            <h3 style="margin-bottom: 8px;">Found Part: <span style="color: var(--accent-primary);">${part.part_number}</span></h3>
            <p style="margin-bottom: 12px; font-size: 0.9em; color: var(--text-muted);">Manufacturer: ${part.manufacturer}</p>
            <div style="display:flex; flex-direction:column; gap:8px;">
        `;
        
        if (result.sources && result.sources.length > 0) {
            result.sources.forEach(src => {
                html += `
                    <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 4px; border-left: 3px solid var(--accent-primary);">
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                            <strong>${src.supplier}</strong>
                            <span style="color:#4cd137; font-weight:bold;">${src.price}</span>
                        </div>
                        <div style="font-size:0.85em; color:var(--text-muted); margin-bottom:8px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">${src.snippet}</div>
                        <div style="display:flex; gap:8px;">
                            <a href="${src.url}" target="_blank" style="font-size:0.85em; color:var(--accent-primary); text-decoration:none;">View Product ↗</a>
                            <a href="javascript:void(0)" onclick="window.draftOutreach('${part.part_number}', 'supplier@example.com')" style="font-size:0.85em; color:#fff; text-decoration:underline;">Contact Supplier (RFQ)</a>
                        </div>
                    </div>
                `;
            });
        } else {
            html += `<div style="color:var(--text-muted);">No commercial sources found online.</div>`;
        }
        html += `</div>`;
        content.innerHTML = html;
        
    } catch (e) {
        loader.style.display = 'none';
        content.style.display = 'block';
        content.innerHTML = `<div style="color:#ff6b6b; padding:12px; background:rgba(255,0,0,0.1); border-radius:4px;">Error: ${e.message}</div>`;
        btn.style.display = 'block';
        btn.textContent = 'Retry Auto-Source';
    }
}

window.draftOutreach = async (partName, supplierEmail) => {
    try {
        const res = await fetch('/api/supplier_outreach', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ part_name: partName, supplier_email: supplierEmail, send_auto: false })
        });
        const data = await res.json();
        
        if (data.status === 'draft') {
            const mailto = `mailto:${supplierEmail}?subject=${encodeURIComponent(data.subject)}&body=${encodeURIComponent(data.body)}`;
            window.location.href = mailto;
        } else if (data.status === 'success') {
            alert('Email sent successfully via SMTP!');
        } else {
            alert('Error generating email: ' + data.error);
        }
    } catch(e) {
        alert('Failed to trigger outreach: ' + e.message);
    }
}

window.findVendors = async (noticeId, title, state, naicsCode) => {
    const btn = document.getElementById('findVendorsBtn');
    const box = document.getElementById('vendorFinderBox');
    const loader = document.getElementById('vendorLoader');
    const content = document.getElementById('vendorContent');
    
    btn.style.display = 'none';
    box.style.display = 'block';
    loader.style.display = 'flex';
    content.style.display = 'none';
    
    try {
        const response = await fetch('/api/find_vendors', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ noticeId, title, state, naicsCode })
        });
        const result = await response.json();
        
        if (!response.ok) throw new Error(result.error || result.message);
        
        loader.style.display = 'none';
        content.style.display = 'block';
        
        const vendors = result.vendors || [];
        if (vendors.length === 0) {
            content.innerHTML = `<div style="color:var(--text-muted); text-align:center;">No qualified vendors found in ${state || 'the specified area'}. Try broadening your search on SAM.gov Entity search.</div>`;
            return;
        }
        
        let html = `<h3 style="margin-bottom:12px; color:var(--accent-secondary);">🏢 Qualified Vendors in ${state || 'Area'}</h3>`;
        html += `<p style="font-size:0.85em; color:var(--text-muted); margin-bottom:16px;">${vendors.length} vendor(s) found matching NAICS ${naicsCode || 'related codes'}</p>`;
        html += `<div style="display:flex; flex-direction:column; gap:10px;">`;
        
        vendors.forEach(v => {
            html += `
                <div class="vendor-card">
                    <div class="vendor-name">${v.name}</div>
                    <div class="vendor-location">📍 ${v.city || ''}, ${v.state || state} ${v.zip || ''}</div>
                    ${v.certs && v.certs.length > 0 ? `
                        <div class="vendor-certs">
                            ${v.certs.map(c => `<span class="cert-tag">${c}</span>`).join('')}
                        </div>` : ''}
                    <div style="display:flex; gap:8px; flex-wrap:wrap;">
                        ${v.uei ? `<span style="font-size:0.8em; color:var(--text-muted);">UEI: ${v.uei}</span>` : ''}
                        ${v.cage ? `<span style="font-size:0.8em; color:var(--text-muted);">CAGE: ${v.cage}</span>` : ''}
                    </div>
                    <div style="margin-top:10px; display:flex; gap:8px;">
                        ${v.sam_url ? `<a href="${v.sam_url}" target="_blank" style="font-size:0.85em; color:var(--accent-primary); text-decoration:none;">View on SAM ↗</a>` : ''}
                        <a href="javascript:void(0)" onclick="window.draftOutreach('${(title || '').replace(/'/g, '')}', '${v.email || 'contractor@example.com'}')" style="font-size:0.85em; color:#fff; text-decoration:underline;">Send RFQ ✉️</a>
                    </div>
                </div>
            `;
        });
        
        html += `</div>`;
        content.innerHTML = html;
        
    } catch (e) {
        loader.style.display = 'none';
        content.style.display = 'block';
        content.innerHTML = `<div style="color:#ff6b6b; padding:12px; background:rgba(255,0,0,0.1); border-radius:4px;">Error: ${e.message}</div>`;
        btn.style.display = 'block';
        btn.textContent = 'Retry Vendor Search';
    }
}

function closeModal() {
    els.modalOverlay.style.display = 'none';
}

// Start
document.addEventListener('DOMContentLoaded', init);
