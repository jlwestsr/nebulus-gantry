# flake8: noqa: E501
MODEL_BUILDER_HTML = """
<div id="model-builder-modal" class="modal hidden">
    <div class="modal-content card">
        <div class="card-header">
            <h2>Build Custom Model</h2>
            <button id="close-builder-btn" class="icon-btn">&times;</button>
        </div>
        <div class="card-body">
            <form id="model-builder-form">
                <div class="form-group">
                    <label for="builder-name">Model Name</label>
                    <input type="text" id="builder-name"
                           placeholder="e.g. pirate-bot" required />
                </div>
                <div class="form-group">
                    <label for="builder-base">Base Model</label>
                    <select id="builder-base" required>
                        <!-- Injected by JS -->
                        <option value="">Loading models...</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="builder-system">System Prompt</label>
                    <textarea id="builder-system"
                              placeholder="You are a helpful assistant..."
                              rows="4"></textarea>
                </div>
                <div class="form-group">
                    <label>Parameters (Optional)</label>
                    <div class="param-row">
                        <span>Temperature</span>
                        <input type="number" id="builder-temp" step="0.1"
                               min="0" max="2" value="0.7" />
                    </div>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary"
                            id="create-model-btn">Create Model</button>
                </div>
            </form>
            <div id="builder-status" class="status-msg hidden"></div>
        </div>
    </div>
</div>
"""

MODEL_BUILDER_CSS = ""  # Deprecated, moved to public/workspace.css
