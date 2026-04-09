/**
 * Database Explorer - Interactive table viewer
 */

class DatabaseExplorer {
    constructor() {
        this.currentTable = null;
        this.currentPage = 0;
        this.pageSize = 100;
        this.totalRecords = 0;

        this.elements = {
            welcomeState: document.getElementById('welcomeState'),
            tableView: document.getElementById('tableView'),
            loadingState: document.getElementById('loadingState'),
            errorState: document.getElementById('errorState'),
            currentTableName: document.getElementById('currentTableName'),
            recordCount: document.getElementById('recordCount'),
            tableHead: document.getElementById('tableHead'),
            tableBody: document.getElementById('tableBody'),
            schemaBody: document.getElementById('schemaBody'),
            dataTab: document.getElementById('dataTab'),
            schemaTab: document.getElementById('schemaTab'),
            pageInfo: document.getElementById('pageInfo'),
            prevBtn: document.getElementById('prevBtn'),
            nextBtn: document.getElementById('nextBtn'),
            errorMessage: document.getElementById('errorMessage')
        };

        this.init();
    }

    init() {
        // Set up event listeners
        this.setupKeyboardShortcuts();
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.currentTable) {
                this.showWelcome();
            }
        });
    }

    showWelcome() {
        this.currentTable = null;
        this.elements.welcomeState.classList.remove('hidden');
        this.elements.tableView.classList.add('hidden');
    }

    showLoading() {
        this.elements.loadingState.classList.remove('hidden');
        this.elements.dataTab.style.opacity = '0.3';
        this.elements.schemaTab.style.opacity = '0.3';
    }

    hideLoading() {
        this.elements.loadingState.classList.add('hidden');
        this.elements.dataTab.style.opacity = '1';
        this.elements.schemaTab.style.opacity = '1';
    }

    showError(message) {
        this.elements.errorMessage.textContent = message;
        this.elements.errorState.classList.remove('hidden');
        this.elements.dataTab.classList.add('hidden');
    }

    hideError() {
        this.elements.errorState.classList.add('hidden');
    }

    async loadTable(tableName, page = 0) {
        this.currentTable = tableName;
        this.currentPage = page;

        // Show table view
        this.elements.welcomeState.classList.add('hidden');
        this.elements.tableView.classList.remove('hidden');
        this.hideError();

        // Update header
        this.elements.currentTableName.textContent = tableName;

        // Show loading
        this.showLoading();

        try {
            const offset = page * this.pageSize;
            const response = await fetch(`/api/table/${tableName}?limit=${this.pageSize}&offset=${offset}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            this.totalRecords = data.total;
            this.elements.recordCount.textContent = `${this.totalRecords.toLocaleString()} records`;

            this.renderTable(data);
            this.updatePagination();

            this.hideLoading();
        } catch (error) {
            console.error('Error loading table:', error);
            this.hideLoading();
            this.showError(`Failed to load table: ${error.message}`);
        }
    }

    renderTable(data) {
        // Clear existing content
        this.elements.tableHead.innerHTML = '';
        this.elements.tableBody.innerHTML = '';

        if (!data.rows || data.rows.length === 0) {
            this.elements.tableBody.innerHTML = `
                <tr>
                    <td colspan="100" style="text-align: center; padding: 2rem; color: var(--text-dim);">
                        No data available
                    </td>
                </tr>
            `;
            return;
        }

        // Create header
        const headerRow = document.createElement('tr');
        data.columns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            headerRow.appendChild(th);
        });
        this.elements.tableHead.appendChild(headerRow);

        // Create rows
        data.rows.forEach(row => {
            const tr = document.createElement('tr');
            data.columns.forEach(col => {
                const td = document.createElement('td');
                let value = row[col];

                // Format value
                if (value === null || value === undefined) {
                    td.textContent = 'NULL';
                    td.style.color = 'var(--text-dim)';
                    td.style.fontStyle = 'italic';
                } else if (typeof value === 'object') {
                    td.textContent = JSON.stringify(value);
                } else {
                    td.textContent = String(value);
                }

                tr.appendChild(td);
            });
            this.elements.tableBody.appendChild(tr);
        });
    }

    async loadSchema(tableName) {
        this.currentTable = tableName;

        // Show table view
        this.elements.welcomeState.classList.add('hidden');
        this.elements.tableView.classList.remove('hidden');
        this.hideError();

        // Update header
        this.elements.currentTableName.textContent = `${tableName} - Schema`;

        // Switch to schema tab
        switchTab('schema');

        // Show loading
        this.showLoading();

        try {
            const response = await fetch(`/api/table/${tableName}/schema`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.renderSchema(data.schema);

            this.hideLoading();
        } catch (error) {
            console.error('Error loading schema:', error);
            this.hideLoading();
            this.showError(`Failed to load schema: ${error.message}`);
        }
    }

    renderSchema(schema) {
        this.elements.schemaBody.innerHTML = '';

        if (!schema || schema.length === 0) {
            this.elements.schemaBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-dim);">
                        No schema information available
                    </td>
                </tr>
            `;
            return;
        }

        schema.forEach(field => {
            const tr = document.createElement('tr');

            ['Field', 'Type', 'Null', 'Key', 'Default', 'Extra'].forEach(col => {
                const td = document.createElement('td');
                let value = field[col];

                if (value === null || value === '') {
                    td.textContent = '—';
                    td.style.color = 'var(--text-dim)';
                } else {
                    td.textContent = String(value);

                    // Highlight primary keys
                    if (col === 'Key' && value === 'PRI') {
                        td.style.color = 'var(--accent)';
                        td.style.fontWeight = '600';
                    }
                }

                tr.appendChild(td);
            });

            this.elements.schemaBody.appendChild(tr);
        });
    }

    updatePagination() {
        const totalPages = Math.ceil(this.totalRecords / this.pageSize);
        const currentPage = this.currentPage + 1;

        this.elements.pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;

        this.elements.prevBtn.disabled = this.currentPage === 0;
        this.elements.nextBtn.disabled = this.currentPage >= totalPages - 1;
    }

    nextPage() {
        if (this.currentTable) {
            this.loadTable(this.currentTable, this.currentPage + 1);
        }
    }

    previousPage() {
        if (this.currentTable && this.currentPage > 0) {
            this.loadTable(this.currentTable, this.currentPage - 1);
        }
    }

    refreshCurrentTable() {
        if (this.currentTable) {
            this.loadTable(this.currentTable, this.currentPage);
        }
    }

    retryLoad() {
        this.hideError();
        if (this.currentTable) {
            this.loadTable(this.currentTable, this.currentPage);
        }
    }

    exportTable() {
        if (!this.currentTable) return;

        // Simple CSV export
        const table = document.getElementById('dataTable');
        const rows = Array.from(table.querySelectorAll('tr'));

        const csv = rows.map(row => {
            const cells = Array.from(row.querySelectorAll('th, td'));
            return cells.map(cell => {
                const text = cell.textContent;
                return text.includes(',') ? `"${text}"` : text;
            }).join(',');
        }).join('\n');

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.currentTable}_export.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// Tab switching
function switchTab(tabName) {
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => tab.classList.remove('active'));
    contents.forEach(content => content.classList.remove('active'));

    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

// Global instance
let explorer;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    explorer = new DatabaseExplorer();
});

// Global functions for button onclick handlers
function loadTable(tableName) {
    explorer.loadTable(tableName);
}

function loadSchema(tableName) {
    explorer.loadSchema(tableName);
}

function nextPage() {
    explorer.nextPage();
}

function previousPage() {
    explorer.previousPage();
}

function refreshCurrentTable() {
    explorer.refreshCurrentTable();
}

function retryLoad() {
    explorer.retryLoad();
}

function exportTable() {
    explorer.exportTable();
}
