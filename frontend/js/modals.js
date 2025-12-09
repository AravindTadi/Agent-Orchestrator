function injectModals() {
    const modalHtml = `
    <!-- Settings Modal -->
    <div id="settings-modal" class="modal-overlay" style="display:none;">
        <div class="modal-dialog settings-dialog">
            <div class="modal-header">
                <h3>Integration Settings</h3>
                <button class="close-btn" onclick="closeSettings()">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
                    </svg>
                </button>
            </div>

            <div class="settings-tabs">
                <button class="settings-tab active" onclick="switchSettingsTab('aws')">AWS CloudWatch</button>
                <button class="settings-tab" onclick="switchSettingsTab('datadog')">Datadog</button>
            </div>

            <div id="aws-settings" class="settings-content">
                <div class="form-group-sm">
                    <label>Access Key ID</label>
                    <input type="text" id="aws-access-key" placeholder="AKIA...">
                </div>
                <div class="form-group-sm">
                    <label>Secret Access Key</label>
                    <input type="password" id="aws-secret-key" placeholder="Secret Key">
                </div>
                <div class="form-group-sm">
                    <label>Region</label>
                    <input type="text" id="aws-region" placeholder="us-east-1" value="us-east-1">
                </div>
                <div class="form-group-sm">
                    <label>Log Group</label>
                    <input type="text" id="aws-log-group" placeholder="/agenthub/logs" value="/agenthub/logs">
                </div>
                <button class="modal-btn modal-btn-primary" onclick="saveAwsSettings()">Save AWS Config</button>
            </div>

            <div id="datadog-settings" class="settings-content" style="display:none;">
                <div class="form-group-sm">
                    <label>API Key</label>
                    <input type="password" id="dd-api-key" placeholder="Datadog API Key">
                </div>
                <div class="form-group-sm">
                    <label>Site</label>
                    <select id="dd-site">
                        <option value="datadoghq.com">datadoghq.com (US)</option>
                        <option value="datadoghq.eu">datadoghq.eu (EU)</option>
                        <option value="us3.datadoghq.com">us3.datadoghq.com</option>
                        <option value="us5.datadoghq.com">us5.datadoghq.com</option>
                    </select>
                </div>
                <button class="modal-btn modal-btn-primary" onclick="saveDatadogSettings()">Save Datadog Config</button>
            </div>
        </div>
    </div>

    <!-- Region Selector Modal -->
    <div class="modal-overlay" id="region-modal" onclick="closeRegionModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h3>Select Region</h3>
                <button class="modal-close" onclick="closeRegionModal()">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
                    </svg>
                </button>
            </div>
            <div class="modal-body">
                <div class="region-list">
                    <div class="region-option active" onclick="selectRegion('us-east-1', 'US East (N. Virginia)')">
                        <span class="region-flag">US</span>
                        <div class="region-details">
                            <span class="region-name">US East (N. Virginia)</span>
                            <span class="region-code">us-east-1</span>
                        </div>
                        <svg class="region-check" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                        </svg>
                    </div>
                    <div class="region-option" onclick="selectRegion('us-west-2', 'US West (Oregon)')">
                        <span class="region-flag">US</span>
                        <div class="region-details">
                            <span class="region-name">US West (Oregon)</span>
                            <span class="region-code">us-west-2</span>
                        </div>
                        <svg class="region-check" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                        </svg>
                    </div>
                    <div class="region-option" onclick="selectRegion('eu-west-1', 'Europe (Ireland)')">
                        <span class="region-flag">EU</span>
                        <div class="region-details">
                            <span class="region-name">Europe (Ireland)</span>
                            <span class="region-code">eu-west-1</span>
                        </div>
                        <svg class="region-check" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                        </svg>
                    </div>
                    <div class="region-option" onclick="selectRegion('ap-southeast-1', 'Asia Pacific (Singapore)')">
                        <span class="region-flag">SG</span>
                        <div class="region-details">
                            <span class="region-name">Asia Pacific (Singapore)</span>
                            <span class="region-code">ap-southeast-1</span>
                        </div>
                        <svg class="region-check" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                        </svg>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- API Keys Modal -->
    <div class="modal-overlay" id="apikeys-modal" onclick="closeApiKeysModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h3>API Keys</h3>
                <button class="modal-close" onclick="closeApiKeysModal()">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
                    </svg>
                </button>
            </div>
            <div class="modal-body">
                <p style="color: var(--text-secondary); margin-bottom: 16px; font-size: 0.9rem;">
                    Use API keys to access AgentHub programmatically. Keep your keys secure.
                </p>
                <div class="api-key-item">
                    <input type="text" id="api-key-display" value="ah_xxxxxxxxxxxxxxxxxxxx" readonly>
                    <div class="api-key-actions">
                        <button class="api-key-btn" onclick="copyApiKey()" title="Copy">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z" />
                            </svg>
                        </button>
                        <button class="api-key-btn" onclick="regenerateApiKey()" title="Regenerate">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z" />
                            </svg>
                        </button>
                    </div>
                </div>
                <button class="generate-key-btn" onclick="generateNewApiKey()">
                    + Generate New API Key
                </button>
            </div>
        </div>
    </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// Inject modals when DOM is ready
document.addEventListener('DOMContentLoaded', injectModals);
