/**
 * Authentication Module
 */

const auth = {
  async login(username_or_email, password) {
    const res = await api.post("/auth/login", { username_or_email, password });
    api.setToken(res.access_token);
    
    // Fetch profile
    const profile = await api.get("/auth/me");
    api.setUser(profile);
    return profile;
  },

  logout() {
    api.clearSession();
    window.location.hash = "#login";
    window.renderApp();
  },

  isAuthenticated() {
    return !!api.getToken();
  },

  getCurrentRole() {
    const user = api.getUser();
    return user ? user.role : null;
  }
};
