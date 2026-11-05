/**
 * Application Core & Routing Handler
 */

window.addEventListener("DOMContentLoaded", () => {
  window.addEventListener("hashchange", renderApp);
  renderApp();
});

function navigate(hash) {
  window.location.hash = hash;
}

async function renderApp() {
  const app = document.getElementById("app");
  const token = api.getToken();
  const currentHash = window.location.hash || "#dashboard";

  if (!token || currentHash === "#login") {
    renderLoginView(app);
    return;
  }

  const user = api.getUser();
  if (!user) {
    try {
      const profile = await api.get("/auth/me");
      api.setUser(profile);
      renderApp();
    } catch {
      auth.logout();
    }
    return;
  }

  // Render Layout Wrapper
  app.innerHTML = `
    <div id="sidebar">
      <a href="#dashboard" class="brand">
        <i class="bi bi-wallet2 text-primary"></i>
        <span>PayrollPro</span>
      </a>
      <div class="nav flex-column mt-3">
        ${getSidebarLinks(user.role, currentHash)}
      </div>
    </div>

    <div id="main-wrapper">
      <div id="topbar">
        <div class="d-flex align-items-center gap-3">
          <h5 class="m-0 text-capitalize fw-bold" id="page-title">${getPageTitle(currentHash)}</h5>
        </div>
        <div class="user-badge">
          <div class="avatar-circle">${user.username.charAt(0).toUpperCase()}</div>
          <div class="d-none d-md-block text-start">
            <div class="fw-semibold small">${user.email}</div>
            <span class="badge bg-secondary" style="font-size:0.7rem;">${user.role}</span>
          </div>
          <button class="btn btn-sm btn-outline-danger ms-2" onclick="auth.logout()" title="Logout">
            <i class="bi bi-box-arrow-right"></i>
          </button>
        </div>
      </div>
      <div class="content-body" id="page-content">
        <div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div></div>
      </div>
    </div>
  `;

  // Route to sub-view
  routePage(currentHash, user);
}

function getSidebarLinks(role, currentHash) {
  let links = `
    <div class="nav-section-title">Overview</div>
    <a class="nav-link ${currentHash === "#dashboard" ? "active" : ""}" onclick="navigate('#dashboard')">
      <i class="bi bi-speedometer2"></i> Dashboard
    </a>
  `;

  if (role === "ADMIN" || role === "HR_MANAGER") {
    links += `
      <div class="nav-section-title">Human Resources</div>
      <a class="nav-link ${currentHash === "#employees" ? "active" : ""}" onclick="navigate('#employees')">
        <i class="bi bi-people"></i> Employees
      </a>
      <a class="nav-link ${currentHash === "#attendance" ? "active" : ""}" onclick="navigate('#attendance')">
        <i class="bi bi-calendar-check"></i> Attendance
      </a>
      <a class="nav-link ${currentHash === "#leaves" ? "active" : ""}" onclick="navigate('#leaves')">
        <i class="bi bi-calendar2-range"></i> Leave Approvals
      </a>
      <div class="nav-section-title">Payroll Management</div>
      <a class="nav-link ${currentHash === "#salary" ? "active" : ""}" onclick="navigate('#salary')">
        <i class="bi bi-cash-stack"></i> Salary Packages
      </a>
      <a class="nav-link ${currentHash === "#payroll" ? "active" : ""}" onclick="navigate('#payroll')">
        <i class="bi bi-credit-card-2-front"></i> Process Payroll
      </a>
      <a class="nav-link ${currentHash === "#payslips" ? "active" : ""}" onclick="navigate('#payslips')">
        <i class="bi bi-file-earmark-pdf"></i> Payslips Registry
      </a>
    `;
  }

  if (role === "EMPLOYEE") {
    links += `
      <div class="nav-section-title">Self-Service</div>
      <a class="nav-link ${currentHash === "#my-profile" ? "active" : ""}" onclick="navigate('#my-profile')">
        <i class="bi bi-person-badge"></i> My Profile
      </a>
      <a class="nav-link ${currentHash === "#my-attendance" ? "active" : ""}" onclick="navigate('#my-attendance')">
        <i class="bi bi-calendar-check"></i> My Attendance
      </a>
      <a class="nav-link ${currentHash === "#my-leaves" ? "active" : ""}" onclick="navigate('#my-leaves')">
        <i class="bi bi-calendar2-plus"></i> Apply / View Leaves
      </a>
      <a class="nav-link ${currentHash === "#my-payslips" ? "active" : ""}" onclick="navigate('#my-payslips')">
        <i class="bi bi-file-earmark-pdf"></i> My Payslips
      </a>
    `;
  }

  return links;
}

function getPageTitle(hash) {
  switch (hash) {
    case "#dashboard": return "Dashboard Overview";
    case "#employees": return "Employee Management";
    case "#attendance": return "Attendance Tracking";
    case "#leaves": return "Leave Approvals";
    case "#salary": return "Salary Components & Structures";
    case "#payroll": return "Monthly Payroll Operations";
    case "#payslips": return "Payslips Archive";
    case "#my-profile": return "My Employee Profile";
    case "#my-attendance": return "My Attendance History";
    case "#my-leaves": return "Leave Management";
    case "#my-payslips": return "My Payslips & Downloads";
    default: return "Payroll System";
  }
}

async function routePage(hash, user) {
  const container = document.getElementById("page-content");
  try {
    switch (hash) {
      case "#dashboard":
        await views.renderDashboard(container, user);
        break;
      case "#employees":
        await views.renderEmployees(container);
        break;
      case "#attendance":
        await views.renderAttendance(container);
        break;
      case "#leaves":
        await views.renderLeaves(container);
        break;
      case "#salary":
        await views.renderSalary(container);
        break;
      case "#payroll":
        await views.renderPayroll(container, user);
        break;
      case "#payslips":
        await views.renderPayslips(container);
        break;
      case "#my-profile":
        await views.renderEmployeeProfile(container);
        break;
      case "#my-attendance":
        await views.renderEmployeeAttendance(container);
        break;
      case "#my-leaves":
        await views.renderEmployeeLeaves(container);
        break;
      case "#my-payslips":
        await views.renderEmployeePayslips(container);
        break;
      default:
        container.innerHTML = `<div class="alert alert-warning">Page not found or under development.</div>`;
    }
  } catch (err) {
    container.innerHTML = `
      <div class="alert alert-danger">
        <h5>Failed to load view</h5>
        <p>${err.message}</p>
        <button class="btn btn-outline-danger btn-sm" onclick="renderApp()">Retry</button>
      </div>
    `;
  }
}

function renderLoginView(app) {
  app.innerHTML = `
    <div class="container d-flex justify-content-center align-items-center" style="min-height: 100vh;">
      <div class="card shadow-lg p-4" style="max-width: 420px; width: 100%; border-radius: 16px; border: none;">
        <div class="text-center mb-4">
          <div class="avatar-circle mx-auto mb-2" style="width: 52px; height: 52px; font-size: 1.4rem;">
            <i class="bi bi-wallet2"></i>
          </div>
          <h4 class="fw-bold m-0">Payroll Management</h4>
          <p class="text-muted small">Sign in to your organization account</p>
        </div>

        <div id="login-alert" class="d-none alert alert-danger py-2 small"></div>

        <form id="login-form">
          <div class="mb-3">
            <label class="form-label small fw-semibold">Email or Username</label>
            <div class="input-group">
              <span class="input-group-text"><i class="bi bi-person"></i></span>
              <input type="text" id="username_or_email" class="form-control" placeholder="e.g. admin@payroll.com" required value="admin@payroll.com">
            </div>
          </div>
          <div class="mb-3">
            <label class="form-label small fw-semibold">Password</label>
            <div class="input-group">
              <span class="input-group-text"><i class="bi bi-lock"></i></span>
              <input type="password" id="password" class="form-control" placeholder="••••••••" required value="Admin@123">
            </div>
          </div>
          <button type="submit" id="login-btn" class="btn btn-primary w-100 fw-semibold py-2">
            Sign In
          </button>
        </form>

        <div class="mt-4 pt-3 border-top text-center">
          <span class="small text-muted">Test demo logins:</span><br/>
          <button class="btn btn-link btn-sm p-0 me-2 text-decoration-none" onclick="setDemo('admin@payroll.com','Admin@123')">Admin</button>
          <button class="btn btn-link btn-sm p-0 me-2 text-decoration-none" onclick="setDemo('hr@payroll.com','Hr@123')">HR</button>
          <button class="btn btn-link btn-sm p-0 text-decoration-none" onclick="setDemo('employee@payroll.com','Employee@123')">Employee</button>
        </div>
      </div>
    </div>
  `;

  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("login-btn");
    const alert = document.getElementById("login-alert");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Signing in...`;
    alert.classList.add("d-none");

    try {
      await auth.login(
        document.getElementById("username_or_email").value,
        document.getElementById("password").value
      );
      navigate("#dashboard");
      renderApp();
    } catch (err) {
      alert.textContent = err.message || "Invalid credentials";
      alert.classList.remove("d-none");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `Sign In`;
    }
  });
}

function setDemo(email, pass) {
  document.getElementById("username_or_email").value = email;
  document.getElementById("password").value = pass;
}
