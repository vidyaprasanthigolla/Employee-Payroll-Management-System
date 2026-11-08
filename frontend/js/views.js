/**
 * Views Implementation Module
 * Renders all feature modules: Dashboards, Employees, Attendance, Leaves, Salary, Payroll, Payslips
 */

const views = {
  // -------------------------------------------------------------
  // Dashboard Overview
  // -------------------------------------------------------------
  async renderDashboard(container, user) {
    if (user.role === "EMPLOYEE") {
      await this.renderEmployeeProfile(container);
      return;
    }

    // Admin & HR Dashboard
    const [employeesRes, payrollRes, leavesRes] = await Promise.all([
      api.get("/employees?page=1&page_size=100"),
      api.get("/payroll/records?month=11&year=2026"),
      api.get("/leaves/pending")
    ]);

    const emps = employeesRes.items || [];
    const payrolls = payrollRes || [];
    const pendingLeaves = leavesRes || [];

    const totalEmployees = emps.length;
    const activeEmployees = emps.filter(e => e.status === "ACTIVE").length;
    const totalPayrollGross = payrolls.reduce((acc, p) => acc + parseFloat(p.gross_salary || 0), 0);
    const totalPayrollNet = payrolls.reduce((acc, p) => acc + parseFloat(p.net_salary || 0), 0);

    container.innerHTML = `
      <div class="row g-3 mb-4">
        <div class="col-12 col-sm-6 col-xl-3">
          <div class="kpi-card d-flex align-items-center gap-3">
            <div class="kpi-icon bg-primary bg-opacity-10 text-primary">
              <i class="bi bi-people"></i>
            </div>
            <div>
              <div class="kpi-val">${totalEmployees}</div>
              <div class="kpi-label">Total Employees (${activeEmployees} Active)</div>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-6 col-xl-3">
          <div class="kpi-card d-flex align-items-center gap-3">
            <div class="kpi-icon bg-success bg-opacity-10 text-success">
              <i class="bi bi-currency-dollar"></i>
            </div>
            <div>
              <div class="kpi-val">₹${totalPayrollNet.toLocaleString()}</div>
              <div class="kpi-label">Disbursed Net (Nov 2026)</div>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-6 col-xl-3">
          <div class="kpi-card d-flex align-items-center gap-3">
            <div class="kpi-icon bg-warning bg-opacity-10 text-warning">
              <i class="bi bi-clock-history"></i>
            </div>
            <div>
              <div class="kpi-val">${pendingLeaves.length}</div>
              <div class="kpi-label">Pending Leave Requests</div>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-6 col-xl-3">
          <div class="kpi-card d-flex align-items-center gap-3">
            <div class="kpi-icon bg-info bg-opacity-10 text-info">
              <i class="bi bi-receipt"></i>
            </div>
            <div>
              <div class="kpi-val">${payrolls.length}</div>
              <div class="kpi-label">Payroll Records Processed</div>
            </div>
          </div>
        </div>
      </div>

      <div class="row g-4 mb-4">
        <div class="col-12 col-lg-7">
          <div class="card p-3 shadow-sm border-0 rounded-4">
            <h6 class="fw-bold mb-3"><i class="bi bi-pie-chart me-2"></i>Department Distribution</h6>
            <div style="height: 280px; position: relative;">
              <canvas id="deptChart"></canvas>
            </div>
          </div>
        </div>
        <div class="col-12 col-lg-5">
          <div class="card p-3 shadow-sm border-0 rounded-4">
            <h6 class="fw-bold mb-3"><i class="bi bi-pie-chart-fill me-2"></i>Payroll Status Overview</h6>
            <div style="height: 280px; position: relative;">
              <canvas id="payrollStatusChart"></canvas>
            </div>
          </div>
        </div>
      </div>

      <div class="card p-4 shadow-sm border-0 rounded-4">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h6 class="fw-bold m-0"><i class="bi bi-hourglass-split me-2 text-warning"></i>Pending Leave Queue</h6>
          <button class="btn btn-sm btn-outline-primary" onclick="navigate('#leaves')">Manage Leaves</button>
        </div>
        <div class="table-responsive">
          <table class="table custom-table m-0">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Leave Type</th>
                <th>Dates</th>
                <th>Days</th>
                <th>Reason</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${pendingLeaves.length === 0 ? `<tr><td colspan="6" class="text-center text-muted py-3">No pending leaves to approve.</td></tr>` : 
                pendingLeaves.map(l => `
                  <tr>
                    <td><strong>${l.employee_code}</strong> - ${l.employee_name}</td>
                    <td><span class="badge bg-secondary">${l.leave_type}</span></td>
                    <td>${l.start_date} to ${l.end_date}</td>
                    <td>${l.days}</td>
                    <td>${l.reason || '—'}</td>
                    <td>
                      <button class="btn btn-sm btn-success py-0 px-2" onclick="views.quickApproveLeave(${l.id})">Approve</button>
                    </td>
                  </tr>
                `).join('')
              }
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Render Charts
    setTimeout(() => {
      this.initDashboardCharts(emps, payrolls);
    }, 100);
  },

  initDashboardCharts(emps, payrolls) {
    const deptCounts = {};
    emps.forEach(e => {
      const d = e.department_name || "Unassigned";
      deptCounts[d] = (deptCounts[d] || 0) + 1;
    });

    const ctxDept = document.getElementById("deptChart");
    if (ctxDept) {
      new Chart(ctxDept, {
        type: "bar",
        data: {
          labels: Object.keys(deptCounts),
          datasets: [{
            label: "Headcount",
            data: Object.values(deptCounts),
            backgroundColor: Object.keys(deptCounts).map(dept => {
                const departmentColors = {
                    "Sales & Marketing": "#2563EB",
                    "Finance & Accounts": "#D97706",
                    "Engineering": "#0F766E",
                    "Unassigned": "#7C3AED"
                };

                return departmentColors[dept] || "#64748B";
            }),
            borderRadius: 6,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } }
        }
      });
    }

    const statusCounts = { DRAFT: 0, APPROVED: 0, PAID: 0 };
    payrolls.forEach(p => {
      statusCounts[p.status] = (statusCounts[p.status] || 0) + 1;
    });

    const ctxStatus = document.getElementById("payrollStatusChart");
    if (ctxStatus) {
      new Chart(ctxStatus, {
        type: "doughnut",
        data: {
          labels: Object.keys(statusCounts),
          datasets: [{
            data: Object.values(statusCounts),
            backgroundColor: [
                "#D97706",  // Draft - Orange
                "#64748B",  // Approved - Blue
                "#0F766E"   // Paid - Green
            ],
            borderColor: [
                "#D97706",  
                "#64748B", 
                "#0F766E"
            ],
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false
        }
      });
    }
  },

  async quickApproveLeave(id) {
    try {
      await api.patch(`/leaves/requests/${id}/review`, { status: "APPROVED", admin_remarks: "Approved from Dashboard" });
      renderApp();
    } catch (err) {
      alert(err.message);
    }
  },

  // -------------------------------------------------------------
  // Employees View
  // -------------------------------------------------------------
  async renderEmployees(container) {
    const data = await api.get("/employees?page=1&page_size=50");
    const depts = await api.get("/departments");
    const desigs = await api.get("/designations");

    container.innerHTML = `
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h6 class="fw-bold m-0">Directory (${data.total} registered)</h6>
        <button class="btn btn-primary btn-sm" onclick="views.showCreateEmployeeModal()">
          <i class="bi bi-person-plus me-1"></i> Add Employee
        </button>
      </div>

      <div class="custom-table-container">
        <table class="table custom-table m-0">
          <thead>
            <tr>
              <th>Code</th>
              <th>Full Name</th>
              <th>Department</th>
              <th>Designation</th>
              <th>Employment</th>
              <th>Bank Account</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${data.items.map(e => `
              <tr>
                <td><strong class="text-primary">${e.employee_code}</strong></td>
                <td>
                  <div class="fw-semibold">${e.full_name}</div>
                  <small class="text-muted">${e.email}</small>
                </td>
                <td>${e.department_name || '—'}</td>
                <td>${e.designation_title || '—'}</td>
                <td><span class="badge bg-light text-dark">${e.employment_type}</span></td>
                <td>
                  <div>${e.bank_name || '—'}</div>
                  <small class="text-muted">${e.masked_bank_account}</small>
                </td>
                <td>
                  <span class="badge badge-status-${e.status.toLowerCase()}">${e.status}</span>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  },
  
  async showCreateEmployeeModal() {
    try {
      // Load dropdown data
      const [deptResponse, desigResponse] = await Promise.all([
        api.get("/departments"),
        api.get("/designations")
      ]);

      // Support either array or paginated API responses
      const departments = Array.isArray(deptResponse)
        ? deptResponse
        : (deptResponse.items || []);

      const designations = Array.isArray(desigResponse)
        ? desigResponse
        : (desigResponse.items || []);

      // Remove an older modal if it exists
      document.getElementById("createEmployeeModal")?.remove();

      const modalHTML = `
        <div class="modal fade" id="createEmployeeModal" tabindex="-1">
          <div class="modal-dialog modal-xl modal-dialog-scrollable">
            <div class="modal-content" style="max-height: 95vh; display: flex; flex-direction: column;">
              <div class="modal-header">
                <h5 class="modal-title fw-bold">Add New Employee</h5>
                <button type="button" class="btn-close"
                  data-bs-dismiss="modal"></button>
              </div>

              <form id="create-employee-form" style="display: flex; flex-direction: column; flex: 1; min-height: 0; overflow: hidden;">
                <div class="modal-body" style="overflow-y: auto; flex: 1 1 auto; min-height: 0;">
                  <h6 class="text-primary fw-bold mb-3">Personal Details</h6>

                  <div class="row g-3">
                    <div class="col-md-6">
                      <label class="form-label">First Name *</label>
                      <input name="first_name" class="form-control"
                        maxlength="50" required>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">Last Name *</label>
                      <input name="last_name" class="form-control"
                        maxlength="50" required>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">Phone *</label>
                      <input name="phone" class="form-control"
                        minlength="7" maxlength="20" required>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">Date of Birth *</label>
                      <input type="date" name="date_of_birth"
                        class="form-control" required>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">Gender *</label>
                      <select name="gender" class="form-select" required>
                        <option value="">Select Gender</option>
                        <option value="MALE">Male</option>
                        <option value="FEMALE">Female</option>
                        <option value="OTHER">Other</option>
                      </select>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">Date of Joining *</label>
                      <input type="date" name="date_of_joining"
                        class="form-control" required>
                    </div>

                    <div class="col-12">
                      <label class="form-label">Address</label>
                      <textarea name="address" class="form-control"
                        rows="2"></textarea>
                    </div>
                  </div>

                  <hr>
                  <h6 class="text-primary fw-bold mb-3">Employment Details</h6>

                  <div class="row g-3">
                    <div class="col-md-6">
                      <label class="form-label">Department</label>
                      <select name="department_id" class="form-select">
                        <option value="">Select Department</option>
                        ${departments.map(d =>
                          `<option value="${d.id}">${d.name}</option>`
                        ).join("")}
                      </select>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">Designation</label>
                      <select name="designation_id" class="form-select">
                        <option value="">Select Designation</option>
                        ${designations.map(d =>
                          `<option value="${d.id}">${d.title}</option>`
                        ).join("")}
                      </select>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">Employment Type *</label>
                      <select name="employment_type" class="form-select" required>
                        <option value="FULL_TIME">Full Time</option>
                        <option value="PART_TIME">Part Time</option>
                        <option value="CONTRACT">Contract</option>
                        <option value="INTERN">Intern</option>
                      </select>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">Status *</label>
                      <select name="status" class="form-select" required>
                        <option value="ACTIVE">Active</option>
                        <option value="PROBATION">Probation</option>
                        <option value="RESIGNED">Resigned</option>
                        <option value="TERMINATED">Terminated</option>
                      </select>
                    </div>
                  </div>

                  <hr>
                  <h6 class="text-primary fw-bold mb-3">Bank Details</h6>

                  <div class="row g-3">
                    <div class="col-md-6">
                      <label class="form-label">Bank Name *</label>
                      <input name="bank_name" class="form-control"
                        minlength="2" maxlength="100" required>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">Bank Account Number *</label>
                      <input name="bank_account_number" class="form-control"
                        minlength="5" maxlength="50" required>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">IFSC Code *</label>
                      <input name="ifsc_code" class="form-control"
                        minlength="4" maxlength="20" required>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">PAN Number *</label>
                      <input name="pan_number" class="form-control"
                        minlength="5" maxlength="20" required>
                    </div>
                  </div>

                  <hr>
                  <h6 class="text-primary fw-bold mb-3">Login Account</h6>

                  <div class="row g-3">
                    <div class="col-md-6">
                      <label class="form-label">Employee Email *</label>
                      <input type="email" name="email" class="form-control"
                        required>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">Login Password *</label>
                      <input type="password" name="password"
                        class="form-control" minlength="6" required>
                    </div>
                  </div>

                  <small class="text-muted d-block mt-2">
                    A login account with the Employee role will be created automatically.
                    The employee code will also be generated automatically.
                  </small>
                </div>

                <div class="modal-footer" style="flex-shrink: 0;">
                  <button type="button" class="btn btn-light"
                    data-bs-dismiss="modal">Cancel</button>
                  <button type="submit" id="save-employee-btn"
                    class="btn btn-primary">
                    Save Employee
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      `;

      document.body.insertAdjacentHTML("beforeend", modalHTML);

      const modalElement = document.getElementById("createEmployeeModal");
      const modal = new bootstrap.Modal(modalElement);
      const form = document.getElementById("create-employee-form");
      const saveButton = document.getElementById("save-employee-btn");

      modal.show();

      form.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (!form.reportValidity()) return;

        const formData = new FormData(form);

        const payload = {
          first_name: formData.get("first_name").trim(),
          last_name: formData.get("last_name").trim(),
          phone: formData.get("phone").trim(),
          address: formData.get("address").trim() || null,
          date_of_birth: formData.get("date_of_birth"),
          gender: formData.get("gender"),
          date_of_joining: formData.get("date_of_joining"),
          department_id: formData.get("department_id")
            ? Number(formData.get("department_id")) : null,
          designation_id: formData.get("designation_id")
            ? Number(formData.get("designation_id")) : null,
          employment_type: formData.get("employment_type"),
          status: formData.get("status"),
          bank_name: formData.get("bank_name").trim(),
          bank_account_number: formData.get("bank_account_number").trim(),
          ifsc_code: formData.get("ifsc_code").trim().toUpperCase(),
          pan_number: formData.get("pan_number").trim().toUpperCase(),
          create_login_account: true,
          email: formData.get("email").trim(),
          password: formData.get("password")
        };

        try {
          saveButton.disabled = true;
          saveButton.textContent = "Saving...";

          await api.post("/employees", payload);

          modal.hide();
          alert("Employee created successfully!");

          await this.renderEmployees(
            document.getElementById("page-content")
          );

        } catch (error) {
          alert("Failed to create employee: " + error.message);
        } finally {
          saveButton.disabled = false;
          saveButton.textContent = "Save Employee";
        }
      });

      modalElement.addEventListener("hidden.bs.modal", () => {
        modalElement.remove();
      }, { once: true });

    } catch (error) {
      alert("Unable to open employee form: " + error.message);
    }
  },

  // -------------------------------------------------------------
  // Attendance View
  // -------------------------------------------------------------
  async renderAttendance(container) {
    const emps = await api.get("/employees?page=1&page_size=100");
    container.innerHTML = `
      <div class="card p-3 shadow-sm border-0 rounded-4 mb-4">
        <h6 class="fw-bold mb-3"><i class="bi bi-calendar-check me-2 text-primary"></i>Daily Attendance Punch</h6>
        <form id="mark-attendance-form" class="row g-3">
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Employee</label>
            <select class="form-select form-select-sm" id="att-emp-id" required>
              ${emps.items.map(e => `<option value="${e.id}">${e.employee_code} - ${e.full_name}</option>`).join('')}
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Date</label>
            <input type="date" class="form-control form-control-sm" id="att-date" required value="2026-11-27">
          </div>
          <div class="col-md-2">
            <label class="form-label small fw-semibold">Status</label>
            <select class="form-select form-select-sm" id="att-status" required>
              <option value="PRESENT">PRESENT</option>
              <option value="HALF_DAY">HALF_DAY</option>
              <option value="ABSENT">ABSENT</option>
            </select>
          </div>
          <div class="col-md-2">
            <label class="form-label small fw-semibold">Check-in</label>
            <input type="time" class="form-control form-control-sm" id="att-in" value="09:00">
          </div>
          <div class="col-md-2">
            <label class="form-label small fw-semibold">Check-out</label>
            <input type="time" class="form-control form-control-sm" id="att-out" value="18:00">
          </div>
          <div class="col-12 text-end">
            <button type="submit" class="btn btn-sm btn-primary">Save Attendance</button>
          </div>
        </form>
      </div>

      <div class="alert alert-info py-2 small">
        <i class="bi bi-info-circle me-1"></i> Attendance records directly factor into unpaid loss of pay (LOP) deductions during monthly payroll processing.
      </div>
    `;

    document.getElementById("mark-attendance-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api.post("/attendance/mark", {
          employee_id: parseInt(document.getElementById("att-emp-id").value),
          date: document.getElementById("att-date").value,
          status: document.getElementById("att-status").value,
          check_in: document.getElementById("att-in").value ? `${document.getElementById("att-in").value}:00` : null,
          check_out: document.getElementById("att-out").value ? `${document.getElementById("att-out").value}:00` : null
        });
        alert("Attendance record recorded successfully.");
      } catch (err) {
        alert(err.message);
      }
    });
  },

  // -------------------------------------------------------------
  // Leaves View (HR/Admin Queue)
  // -------------------------------------------------------------
  async renderLeaves(container) {
    const pending = await api.get("/leaves/pending");
    container.innerHTML = `
      <div class="card p-3 shadow-sm border-0 rounded-4">
        <h6 class="fw-bold mb-3"><i class="bi bi-check2-circle me-2 text-primary"></i>Pending Leave Requests</h6>
        <div class="table-responsive">
          <table class="table custom-table m-0">
            <thead>
              <tr>
                <th>Req ID</th>
                <th>Employee</th>
                <th>Leave Type</th>
                <th>Start Date</th>
                <th>End Date</th>
                <th>Days</th>
                <th>Reason</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${pending.length === 0 ? `<tr><td colspan="8" class="text-center text-muted py-3">All leave requests have been reviewed.</td></tr>` : 
                pending.map(l => `
                  <tr>
                    <td>#${l.id}</td>
                    <td><strong>${l.employee_code}</strong> (${l.employee_name})</td>
                    <td><span class="badge bg-secondary">${l.leave_type}</span></td>
                    <td>${l.start_date}</td>
                    <td>${l.end_date}</td>
                    <td>${l.days}</td>
                    <td>${l.reason || '—'}</td>
                    <td>
                      <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-success" onclick="views.reviewLeave(${l.id}, 'APPROVED')">Approve</button>
                        <button class="btn btn-outline-danger" onclick="views.reviewLeave(${l.id}, 'REJECTED')">Reject</button>
                      </div>
                    </td>
                  </tr>
                `).join('')
              }
            </tbody>
          </table>
        </div>
      </div>
    `;
  },

  async reviewLeave(id, status) {
    try {
      await api.patch(`/leaves/requests/${id}/review`, { status, admin_remarks: `Actioned as ${status}` });
      this.renderLeaves(document.getElementById("page-content"));
    } catch (err) {
      alert(err.message);
    }
  },

  // -------------------------------------------------------------
  // Salary Packages View
  // -------------------------------------------------------------
  async renderSalary(container) {
    const components = await api.get("/salary/components");
    container.innerHTML = `
      <div class="card p-3 shadow-sm border-0 rounded-4 mb-4">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h6 class="fw-bold m-0"><i class="bi bi-coin me-2 text-primary"></i>Configured Salary Components</h6>
        </div>
        <div class="table-responsive">
          <table class="table custom-table m-0">
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Type</th>
                <th>Calculation</th>
                <th>Default Amount / %</th>
                <th>Taxable</th>
              </tr>
            </thead>
            <tbody>
              ${components.map(c => `
                <tr>
                  <td><code>${c.code}</code></td>
                  <td><strong>${c.name}</strong></td>
                  <td>
                    <span class="badge ${c.type === 'EARNING' ? 'bg-primary' : 'bg-danger'}">${c.type || 'Not configured'}</span>
                  </td>
                  <td>${c.calculation_type || 'Not configured'}</td>
                  <td>${c.calculation_type === 'PERCENTAGE'
                    ? `${Number(c.default_value ?? 0).toLocaleString('en-IN')}%`
                    : `₹${Number(c.default_value ?? 0).toLocaleString('en-IN')}`}</td>
                  <td>${c.is_taxable ? 'Yes' : 'No'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  },

  // -------------------------------------------------------------
  // Payroll Operations View
  // -------------------------------------------------------------
  async renderPayroll(container, user) {
    const records = await api.get("/payroll/records?month=11&year=2026");

    container.innerHTML = `
      <div class="card p-3 shadow-sm border-0 rounded-4 mb-4">
        <h6 class="fw-bold mb-3"><i class="bi bi-gear-wide-connected me-2 text-primary"></i>Execute Payroll Batch</h6>
        <form id="payroll-run-form" class="row g-3">
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Month</label>
            <select class="form-select form-select-sm" id="pay-month">
              <option value="11" selected>November (11)</option>
              <option value="12">December (12)</option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Year</label>
            <input type="number" class="form-control form-control-sm" id="pay-year" value="2026" required>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Disbursement Method</label>
            <select class="form-select form-select-sm" id="pay-method">
              <option value="BANK_TRANSFER">Bank Transfer (NEFT/RTGS)</option>
              <option value="CHEQUE">Cheque</option>
              <option value="CASH">Cash</option>
            </select>
          </div>
          <div class="col-md-3 d-flex align-items-end">
            <button type="submit" class="btn btn-primary btn-sm w-100">
              <i class="bi bi-calculator me-1"></i> Calculate &amp; Process
            </button>
          </div>
        </form>
      </div>

      <div class="card p-3 shadow-sm border-0 rounded-4">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h6 class="fw-bold m-0"><i class="bi bi-table me-2 text-primary"></i>November 2026 Payroll Records</h6>
        </div>
        <div class="table-responsive">
          <table class="table custom-table m-0">
            <thead>
              <tr>
                <th>Batch</th>
                <th>Employee</th>
                <th>Gross Salary</th>
                <th>Deductions</th>
                <th>LOP Deduct</th>
                <th>Net Salary</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${records.map(r => `
                <tr>
                  <td><code>${r.payroll_batch_code}</code></td>
                  <td><strong>${r.employee_code}</strong><br/><small class="text-muted">${r.employee_name}</small></td>
                  <td>₹${parseFloat(r.gross_salary).toLocaleString()}</td>
                  <td class="text-danger">₹${parseFloat(r.total_deductions).toLocaleString()}</td>
                  <td class="text-warning">₹${parseFloat(r.lop_deduction).toLocaleString()}</td>
                  <td class="fw-bold text-success">₹${parseFloat(r.net_salary).toLocaleString()}</td>
                  <td><span class="badge badge-status-${r.status.toLowerCase()}">${r.status}</span></td>
                  <td>
                    <div class="btn-group btn-group-sm">
                      ${r.status === 'DRAFT' && user.role === 'ADMIN' ? 
                        `<button class="btn btn-outline-primary" onclick="views.approvePayroll(${r.id})">Approve</button>` : ''}
                      ${r.status === 'APPROVED' && user.role === 'ADMIN' ? 
                        `<button class="btn btn-outline-success" onclick="views.payPayroll(${r.id})">Disburse</button>` : ''}
                      ${r.status === 'APPROVED' || r.status === 'PAID' ? 
                        `<button class="btn btn-outline-secondary" onclick="views.generatePayslipModal(${r.id})"><i class="bi bi-file-earmark-pdf"></i> PDF</button>` : ''}
                    </div>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    document.getElementById("payroll-run-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api.post("/payroll/process", {
          month: parseInt(document.getElementById("pay-month").value),
          year: parseInt(document.getElementById("pay-year").value),
          payment_method: document.getElementById("pay-method").value
        });
        alert("Payroll calculation batch completed.");
        this.renderPayroll(container, user);
      } catch (err) {
        alert(err.message);
      }
    });
  },

  async approvePayroll(id) {
    try {
      await api.patch(`/payroll/records/${id}/approve?remarks=Approved+by+Admin`);
      renderApp();
    } catch (err) {
      alert(err.message);
    }
  },

  async payPayroll(id) {
    try {
      await api.patch(`/payroll/records/${id}/pay`, { status: "PAID", payment_date: "2026-11-30" });
      renderApp();
    } catch (err) {
      alert(err.message);
    }
  },

  async generatePayslipModal(payrollId) {
    try {
      const ps = await api.post(`/payslips/generate/${payrollId}`, {});
      alert(`Payslip PDF generated successfully: ${ps.payslip_number}`);
      navigate("#payslips");
    } catch (err) {
      alert(err.message);
    }
  },

  // -------------------------------------------------------------
  // Payslips Archive View
  // -------------------------------------------------------------
  async renderPayslips(container) {
    const list = await api.get("/payslips/");
    container.innerHTML = `
      <div class="card p-3 shadow-sm border-0 rounded-4">
        <h6 class="fw-bold mb-3"><i class="bi bi-archive me-2 text-primary"></i>Generated Payslip Registry</h6>
        <div class="table-responsive">
          <table class="table custom-table m-0">
            <thead>
              <tr>
                <th>Payslip #</th>
                <th>Employee</th>
                <th>Period</th>
                <th>Generated At</th>
                <th>Downloads</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${list.length === 0 ? `<tr><td colspan="6" class="text-center text-muted py-3">No payslips generated yet.</td></tr>` : 
                list.map(p => `
                  <tr>
                    <td><code>${p.payslip_number}</code></td>
                    <td><strong>${p.employee_code}</strong> - ${p.employee_name}</td>
                    <td>${p.month}/${p.year}</td>
                    <td>${new Date(p.generated_at).toLocaleDateString()}</td>
                    <td><span class="badge bg-light text-dark">${p.download_count} times</span></td>
                    <td>
                      <button class="btn btn-sm btn-outline-danger" onclick="api.download('/payslips/${p.id}/download', '${p.payslip_number}.pdf')">
                        <i class="bi bi-download me-1"></i> Download PDF
                      </button>
                    </td>
                  </tr>
                `).join('')
              }
            </tbody>
          </table>
        </div>
      </div>
    `;
  },

  // -------------------------------------------------------------
  // Employee Self-Service Views
  // -------------------------------------------------------------
  async renderEmployeeProfile(container) {
    const emp = await api.get("/employees/me");
    const salary = await api.get("/salary/me");

    container.innerHTML = `
      <div class="row g-4">
        <div class="col-12 col-lg-5">
          <div class="card p-4 shadow-sm border-0 rounded-4">
            <div class="text-center mb-3">
              <div class="avatar-circle mx-auto mb-2" style="width:64px;height:64px;font-size:1.6rem;">
                ${emp.first_name.charAt(0)}
              </div>
              <h5 class="fw-bold m-0">${emp.full_name}</h5>
              <div class="text-muted small">${emp.designation_title} • ${emp.department_name}</div>
              <span class="badge badge-status-${emp.status.toLowerCase()} mt-2">${emp.status}</span>
            </div>
            <hr/>
            <div class="small">
              <div class="d-flex justify-content-between py-1">
                <span class="text-muted">Employee Code:</span>
                <span class="fw-semibold">${emp.employee_code}</span>
              </div>
              <div class="d-flex justify-content-between py-1">
                <span class="text-muted">Date of Joining:</span>
                <span class="fw-semibold">${emp.date_of_joining}</span>
              </div>
              <div class="d-flex justify-content-between py-1">
                <span class="text-muted">Bank Name:</span>
                <span class="fw-semibold">${emp.bank_name}</span>
              </div>
              <div class="d-flex justify-content-between py-1">
                <span class="text-muted">Bank Account:</span>
                <span class="fw-semibold">${emp.masked_bank_account}</span>
              </div>
              <div class="d-flex justify-content-between py-1">
                <span class="text-muted">PAN Number:</span>
                <span class="fw-semibold">${emp.pan_number}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="col-12 col-lg-7">
          <div class="card p-4 shadow-sm border-0 rounded-4">
            <h6 class="fw-bold mb-3"><i class="bi bi-cash-coin me-2 text-primary"></i>My Salary Package</h6>
            <div class="row g-2 mb-3">
              <div class="col-6">
                <div class="p-3 bg-light rounded-3">
                  <div class="small text-muted">Monthly Gross</div>
                  <h4 class="fw-bold text-primary m-0">₹${parseFloat(salary.gross_salary).toLocaleString()}</h4>
                </div>
              </div>
              <div class="col-6">
                <div class="p-3 bg-light rounded-3">
                  <div class="small text-muted">Base Take-Home</div>
                  <h4 class="fw-bold text-success m-0">₹${parseFloat(salary.net_salary).toLocaleString()}</h4>
                </div>
              </div>
            </div>

            <h6 class="small fw-bold text-muted text-uppercase mb-2">Salary Components</h6>
            <div class="table-responsive">
              <table class="table table-sm custom-table m-0">
                <thead>
                  <tr>
                    <th>Component</th>
                    <th>Type</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  ${salary.earnings.map(e => `<tr><td>${e.component_name}</td><td><span class="badge bg-primary">EARNING</span></td><td>₹${parseFloat(e.amount).toLocaleString()}</td></tr>`).join('')}
                  ${salary.deductions.map(d => `<tr><td>${d.component_name}</td><td><span class="badge bg-danger">DEDUCTION</span></td><td class="text-danger">₹${parseFloat(d.amount).toLocaleString()}</td></tr>`).join('')}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  async renderEmployeeAttendance(container) {
    const employee = await api.get("/employees/me");
    const today = new Date();
    const month = today.getMonth() + 1;
    const year = today.getFullYear();

    const [records, summary] = await Promise.all([
      api.get("/attendance/me"),
      api.get(`/attendance/summary/${employee.id}?month=${month}&year=${year}`)
    ]);

    container.innerHTML = `
      <div class="row g-3 mb-4">
        <div class="col-sm-4">
          <div class="kpi-card text-center">
            <div class="kpi-val text-success">${summary.present_days}</div>
            <div class="kpi-label">Present Days</div>
          </div>
        </div>
        <div class="col-sm-4">
          <div class="kpi-card text-center">
            <div class="kpi-val text-warning">${summary.half_days}</div>
            <div class="kpi-label">Half Days</div>
          </div>
        </div>
        <div class="col-sm-4">
          <div class="kpi-card text-center">
            <div class="kpi-val text-danger">${summary.absent_days}</div>
            <div class="kpi-label">Absences (LOP)</div>
          </div>
        </div>
      </div>

      <div class="card p-3 shadow-sm border-0 rounded-4">
        <h6 class="fw-bold mb-3">Attendance History</h6>
        <div class="table-responsive">
          <table class="table custom-table m-0">
            <thead>
              <tr>
                <th>Date</th>
                <th>Status</th>
                <th>Check In</th>
                <th>Check Out</th>
                <th>Hours Worked</th>
              </tr>
            </thead>
            <tbody>
              ${records.map(r => `
                <tr>
                  <td>${r.date}</td>
                  <td><span class="badge bg-light text-dark">${r.status}</span></td>
                  <td>${r.check_in || '—'}</td>
                  <td>${r.check_out || '—'}</td>
                  <td>${r.working_hours ? `${r.working_hours} hrs` : '—'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  },

  async renderEmployeeLeaves(container) {
    const year = new Date().getFullYear();
    const [balances, myRequests] = await Promise.all([
      api.get(`/leaves/balances/me?year=${year}`),
      api.get("/leaves/me")
    ]);

    container.innerHTML = `
      <div class="row g-3 mb-4">
        ${balances.map(b => `
          <div class="col-sm-4">
            <div class="kpi-card">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="badge bg-secondary">${b.leave_type}</span>
                <span class="small text-muted">Total: ${b.total_allocated}</span>
              </div>
              <div class="kpi-val">${b.remaining}</div>
              <div class="kpi-label">Days Available (Used: ${b.used})</div>
            </div>
          </div>
        `).join('')}
      </div>

      <div class="card p-3 shadow-sm border-0 rounded-4 mb-4">
        <h6 class="fw-bold mb-3"><i class="bi bi-send me-2 text-primary"></i>Submit Leave Application</h6>
        <form id="apply-leave-form" class="row g-3">
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Leave Type</label>
            <select class="form-select form-select-sm" id="leave-type" required>
              <option value="CASUAL">Casual Leave</option>
              <option value="SICK">Sick Leave</option>
              <option value="EARNED">Earned Leave</option>
              <option value="UNPAID">Unpaid Leave</option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Start Date</label>
            <input type="date" class="form-control form-control-sm" id="leave-start" required>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">End Date</label>
            <input type="date" class="form-control form-control-sm" id="leave-end" required>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Reason</label>
            <input type="text" class="form-control form-control-sm" id="leave-reason" placeholder="e.g. Doctor appointment">
          </div>
          <div class="col-12 text-end">
            <button type="submit" class="btn btn-primary btn-sm">Submit Request</button>
          </div>
        </form>
      </div>

      <div class="card p-3 shadow-sm border-0 rounded-4">
        <h6 class="fw-bold mb-3">My Leave Application Status</h6>
        <div class="table-responsive">
          <table class="table custom-table m-0">
            <thead>
              <tr>
                <th>Type</th>
                <th>Dates</th>
                <th>Days</th>
                <th>Reason</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${myRequests.map(r => `
                <tr>
                  <td><strong>${r.leave_type}</strong></td>
                  <td>${r.start_date} to ${r.end_date}</td>
                  <td>${r.days}</td>
                  <td>${r.reason || '—'}</td>
                  <td><span class="badge badge-status-${r.status.toLowerCase()}">${r.status}</span></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    document.getElementById("apply-leave-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api.post("/leaves/apply", {
          leave_type: document.getElementById("leave-type").value,
          start_date: document.getElementById("leave-start").value,
          end_date: document.getElementById("leave-end").value,
          reason: document.getElementById("leave-reason").value
        });
        alert("Leave request submitted successfully.");
        await this.renderEmployeeLeaves(container);
      } catch (err) {
        alert(err.message);
      }
    });
  },

  async renderEmployeePayslips(container) {
    const list = await api.get("/payslips/me");
    container.innerHTML = `
      <div class="card p-3 shadow-sm border-0 rounded-4">
        <h6 class="fw-bold mb-3"><i class="bi bi-file-earmark-pdf me-2 text-danger"></i>My Downloadable Payslips</h6>
        <div class="table-responsive">
          <table class="table custom-table m-0">
            <thead>
              <tr>
                <th>Payslip #</th>
                <th>Period</th>
                <th>Generated Date</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${list.length === 0 ? `<tr><td colspan="4" class="text-center text-muted py-3">No payslips available yet.</td></tr>` : 
                list.map(p => `
                  <tr>
                    <td><code>${p.payslip_number}</code></td>
                    <td><strong>${p.month}/${p.year}</strong></td>
                    <td>${new Date(p.generated_at).toLocaleDateString()}</td>
                    <td>
                      <button class="btn btn-sm btn-outline-danger" onclick="api.download('/payslips/${p.id}/download', '${p.payslip_number}.pdf')">
                        <i class="bi bi-download me-1"></i> Download PDF
                      </button>
                    </td>
                  </tr>
                `).join('')
              }
            </tbody>
          </table>
        </div>
      </div>
    `;
  }
};
