import { useEffect, useRef, useState } from "react";
import { BarChart3, Building2, FileText, LayoutGrid, MessageSquare, Trash2, Users } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import AuthForm, { AuthMode } from "./components/AuthForm";
import PageHeader from "./components/PageHeader";
import SidebarNav from "./components/SidebarNav";
import { apiFetch } from "./lib/api";

const navItems = ["Dashboard", "Documents", "Organization", "Usage", "User Management", "Chat"] as const;

type NavItem = (typeof navItems)[number];

type Tenant = {
  id: string;
  name: string;
  slug: string;
  org_id?: string;
};

type OrgInfo = {
  id: string;
  name: string;
  slug: string;
  role: string;
};

type OrgMetrics = {
  total_tenants: number;
  total_users: number;
  total_documents: number;
  total_queries: number;
  by_tenant: Array<{ tenant_id: string; tenant_name: string; documents: number; queries: number }>;
};

type UserOption = {
  id: string;
  name: string;
  email: string;
};

type DocumentItem = {
  id: string;
  title: string;
  status: string;
  source_type: string;
};

type ChunkStrategy = {
  id: string;
  name: string;
  params_json?: Record<string, any>;
  active?: boolean;
};

type SettingsState = {
  llm_provider: string;
  embed_provider: string;
  llm_model: string;
  embed_model: string;
  chunk_strategy_id: string;
  has_openai_key: boolean;
  has_groq_key: boolean;
  has_lattice_key: boolean;
};

type QueryResponse = {
  answer: string;
  citations: Array<{ chunk_id: string; document_id: string; score: number; text: string }>;
  no_answer: boolean;
};

type ChatSession = {
  id: string;
  tenant_id: string;
  user_id: string;
  title?: string | null;
};

type ChatMessage = {
  id: string;
  session_id: string;
  tenant_id: string;
  user_id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Array<{ chunk_id: string; document_id: string; score: number; text: string }>;
};

type ActivityEvent = {
  id: string;
  tenant_id: string;
  tenant_name?: string | null;
  event_type: string;
  payload: Record<string, any>;
  created_at: string;
};

type DocumentPreview = {
  document_id: string;
  title: string;
  status: string;
  source_type: string;
  preview_text: string;
};

const sampleAnalytics = [
  { name: "Mon", queries: 120 },
  { name: "Tue", queries: 180 },
  { name: "Wed", queries: 90 },
  { name: "Thu", queries: 140 },
  { name: "Fri", queries: 210 }
];

export default function App() {
  const [active, setActive] = useState<NavItem>("Dashboard");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [authed, setAuthed] = useState<boolean>(() => Boolean(localStorage.getItem("access_token")));
  const [orgInfo, setOrgInfo] = useState<OrgInfo | null>(null);
  const [orgMetrics, setOrgMetrics] = useState<OrgMetrics | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState<string>("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [uploadTitle, setUploadTitle] = useState<string>("");
  const [uploadTitleEdited, setUploadTitleEdited] = useState(false);
  const [sourceType, setSourceType] = useState<string>("pdf");
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [queryText, setQueryText] = useState("");
  const [querying, setQuerying] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [queryAnswer, setQueryAnswer] = useState<string>("");
  const [queryCitations, setQueryCitations] = useState<QueryResponse["citations"]>([]);
  const [noAnswer, setNoAnswer] = useState<boolean>(false);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [activityEvents, setActivityEvents] = useState<ActivityEvent[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatSending, setChatSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [useSelectedOnly, setUseSelectedOnly] = useState<boolean>(false);
  const [sessionId] = useState<string>(() =>
    typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}`
  );
  const [previewDocId, setPreviewDocId] = useState<string>("");
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<DocumentPreview | null>(null);
  const [highlightText, setHighlightText] = useState<string>("");
  const [highlightMode, setHighlightMode] = useState<"highlight_only" | "highlight_plus_docs">("highlight_only");
  const chatScrollRef = useRef<HTMLDivElement | null>(null);

  const [chunkStrategies, setChunkStrategies] = useState<ChunkStrategy[]>([]);
  const [settingsState, setSettingsState] = useState<SettingsState>({
    llm_provider: "custom",
    embed_provider: "custom",
    llm_model: "",
    embed_model: "",
    chunk_strategy_id: "",
    has_openai_key: false,
    has_groq_key: false,
    has_lattice_key: false
  });
  const [openaiKeyInput, setOpenaiKeyInput] = useState("");
  const [groqKeyInput, setGroqKeyInput] = useState("");
  const [latticeKeyInput, setLatticeKeyInput] = useState("");
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null);
  const [tenantNameInput, setTenantNameInput] = useState("");
  const [tenantSlugInput, setTenantSlugInput] = useState("");
  const [tenantCreateMessage, setTenantCreateMessage] = useState<string | null>(null);
  const [tenantCreating, setTenantCreating] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserName, setNewUserName] = useState("");
  const [newUserTempPassword, setNewUserTempPassword] = useState("");
  const [newUserMessage, setNewUserMessage] = useState<string | null>(null);
  const [newUserResetLink, setNewUserResetLink] = useState<string | null>(null);
  const [newUserId, setNewUserId] = useState<string | null>(null);
  const [newUserLabel, setNewUserLabel] = useState<string | null>(null);
  const [userOptions, setUserOptions] = useState<UserOption[]>([]);
  const [assignTenantId, setAssignTenantId] = useState("");
  const [assignUserId, setAssignUserId] = useState("");
  const [assignRole, setAssignRole] = useState("member");
  const [assignMessage, setAssignMessage] = useState<string | null>(null);
  const [assigning, setAssigning] = useState(false);
  const [resetTokenInput, setResetTokenInput] = useState("");
  const [resetPasswordInput, setResetPasswordInput] = useState("");
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const resetTokenFromUrl = (() => {
    if (typeof window === "undefined") return "";
    const params = new URLSearchParams(window.location.search);
    return params.get("token") || "";
  })();


  const isOrgAdmin = orgInfo?.role === "owner" || orgInfo?.role === "admin";
  const visibleNavItems = isOrgAdmin
    ? navItems
    : navItems.filter((item) => !["Organization", "Usage", "User Management"].includes(item));

  const navIconComponents: Record<NavItem, JSX.Element> = {
    Dashboard: <LayoutGrid className="h-4 w-4" />,
    Documents: <FileText className="h-4 w-4" />,
    Organization: <Building2 className="h-4 w-4" />,
    Usage: <BarChart3 className="h-4 w-4" />,
    "User Management": <Users className="h-4 w-4" />,
    Chat: <MessageSquare className="h-4 w-4" />
  };

  const slugify = (value: string) =>
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)+/g, "");

  const location = useLocation();
  const navigate = useNavigate();
  const routeToNav: Record<string, NavItem> = {
    "/dashboard": "Dashboard",
    "/documents": "Documents",
    "/organization": "Organization",
    "/usage": "Usage",
    "/user-management": "User Management",
    "/chat": "Chat"
  };
  const navToRoute: Record<NavItem, string> = {
    Dashboard: "/dashboard",
    Documents: "/documents",
    Organization: "/organization",
    Usage: "/usage",
    "User Management": "/user-management",
    Chat: "/chat"
  };

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    const mapped = routeToNav[location.pathname];
    if (mapped && mapped !== active) {
      setActive(mapped);
    }
  }, [location.pathname, active]);

  useEffect(() => {
    if (!isOrgAdmin && ["Organization", "Usage", "User Management"].includes(active)) {
      navigate("/dashboard");
    }
  }, [isOrgAdmin, active, navigate]);

  if (typeof window !== "undefined" && window.location.pathname.startsWith("/reset-password")) {
    return (
      <div className="min-h-screen p-6 flex items-center justify-center">
        <div className="card p-8 w-full max-w-md space-y-4">
          <div className="text-center">
            <h1 className="font-display text-2xl">Reset Password</h1>
            <p className="text-sm text-[color:var(--muted)]">Use the link provided by your admin.</p>
          </div>
          <input
            className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
            placeholder="Reset token"
            value={resetTokenInput || resetTokenFromUrl}
            onChange={(e) => setResetTokenInput(e.target.value)}
          />
          <input
            className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
            placeholder="New password"
            type="password"
            value={resetPasswordInput}
            onChange={(e) => setResetPasswordInput(e.target.value)}
          />
          {resetMessage && <div className="text-sm text-[color:var(--muted)]">{resetMessage}</div>}
          <button
            className="w-full px-6 py-2 rounded-xl bg-[color:var(--accent-strong)] text-white"
            onClick={async () => {
              const token = resetTokenInput || resetTokenFromUrl;
              if (!token || !resetPasswordInput.trim()) {
                setResetMessage("Token and password are required.");
                return;
              }
              try {
                await apiFetch("/auth/reset-password", {
                  method: "POST",
                  body: JSON.stringify({ token, new_password: resetPasswordInput })
                });
                setResetMessage("Password updated. You can now log in.");
              } catch (err: any) {
                setResetMessage(err?.message || "Reset failed.");
              }
            }}
          >
            Reset Password
          </button>
        </div>
      </div>
    );
  }

  useEffect(() => {
    if (!authed) return;
    apiFetch("/orgs/me")
      .then((data) => {
        setOrgInfo({
          id: data.organization.id,
          name: data.organization.name,
          slug: data.organization.slug,
          role: data.role
        });
      })
      .catch(() => {
        setOrgInfo(null);
      });
  }, [authed]);

  useEffect(() => {
    if (!authed || !isOrgAdmin) return;
    apiFetch("/orgs/metrics")
      .then((data) => setOrgMetrics(data))
      .catch(() => setOrgMetrics(null));
  }, [authed, isOrgAdmin]);

  useEffect(() => {
    if (!authed) return;
    fetchEvents();
  }, [authed, tenantId]);

  useEffect(() => {
    if (!authed || !isOrgAdmin) return;
    apiFetch("/users")
      .then((data) => setUserOptions(data || []))
      .catch(() => setUserOptions([]));
  }, [authed, isOrgAdmin]);

  useEffect(() => {
    if (!authed) return;
    apiFetch("/tenants")
      .then((data) => {
        setTenants(data || []);
        if (!tenantId && data?.length) {
          const defaultTenant = data.find((t: Tenant) => t.slug === "default");
          setTenantId(defaultTenant ? defaultTenant.id : data[0].id);
        }
      })
      .catch(() => {
        setTenants([]);
      });
  }, [authed, tenantId]);

  const fetchDocuments = () => {
    if (!tenantId) {
      setDocuments([]);
      return;
    }
    apiFetch(`/documents?tenant_id=${tenantId}`)
      .then((data) => setDocuments(data || []))
      .catch(() => setDocuments([]));
  };

  const fetchEvents = () => {
    apiFetch("/events?limit=12")
      .then((data) => setActivityEvents(data || []))
      .catch(() => setActivityEvents([]));
  };

  const fetchChatSessions = async () => {
    if (!tenantId) {
      setChatSessions([]);
      setActiveSessionId("");
      setChatMessages([]);
      return;
    }
    try {
      const data = await apiFetch(`/chat/sessions?tenant_id=${tenantId}`);
      setChatSessions(data || []);
      if (data?.length) {
        const stillExists = data.find((session: ChatSession) => session.id === activeSessionId);
        setActiveSessionId(stillExists ? stillExists.id : data[0].id);
      } else if (isOrgAdmin || tenantId) {
        const created = await apiFetch("/chat/sessions", {
          method: "POST",
          body: JSON.stringify({ tenant_id: tenantId, title: "New Chat" })
        });
        setChatSessions([created]);
        setActiveSessionId(created.id);
      }
    } catch {
      setChatSessions([]);
    }
  };

  const fetchChatMessages = async (sessionId: string) => {
    if (!sessionId) {
      setChatMessages([]);
      return;
    }
    try {
      const data = await apiFetch(`/chat/messages?session_id=${sessionId}`);
      setChatMessages(data || []);
    } catch {
      setChatMessages([]);
    }
  };

  const fetchChunkStrategies = () => {
    apiFetch("/chunk-strategies")
      .then((data) => setChunkStrategies(data || []))
      .catch(() => setChunkStrategies([]));
  };

  const fetchUserSettings = () => {
    if (!tenantId) return;
    apiFetch(`/settings?tenant_id=${tenantId}`)
      .then((data) => {
        setSettingsState({
          llm_provider: data.llm_provider || "custom",
          embed_provider: data.embed_provider || "custom",
          llm_model: data.llm_model || "",
          embed_model: data.embed_model || "",
          chunk_strategy_id: data.chunk_strategy_id || "",
          has_openai_key: Boolean(data.has_openai_key),
          has_groq_key: Boolean(data.has_groq_key),
          has_lattice_key: Boolean(data.has_lattice_key)
        });
      })
      .catch(() => {
        setSettingsState({
          llm_provider: "custom",
          embed_provider: "custom",
          llm_model: "",
          embed_model: "",
          chunk_strategy_id: "",
          has_openai_key: false,
          has_groq_key: false,
          has_lattice_key: false
        });
      });
  };

  useEffect(() => {
    if (!authed) return;
    fetchChunkStrategies();
  }, [authed]);

  useEffect(() => {
    if (!authed) return;
    fetchDocuments();
    fetchUserSettings();
    fetchChatSessions();
    setSelectedDocIds([]);
    setPreviewDocId("");
    setPreviewData(null);
    setHighlightText("");
  }, [authed, tenantId]);

  useEffect(() => {
    if (!authed) return;
    fetchChatMessages(activeSessionId);
  }, [authed, activeSessionId]);

  useEffect(() => {
    if (!chatScrollRef.current) return;
    chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
  }, [chatMessages.length]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    setSelectedFiles(files);
    if (!uploadTitleEdited && files.length > 0) {
      setUploadTitle(files[0].name);
    }
  };

  const handleUpload = async () => {
    if (!tenantId) {
      setUploadMessage("Select a tenant before uploading.");
      return;
    }
    if (!selectedFiles.length) {
      setUploadMessage("Choose a file to upload.");
      return;
    }
    const file = selectedFiles[0];
    const formData = new FormData();
    formData.append("tenant_id", tenantId);
    formData.append("title", uploadTitle || file.name);
    formData.append("source_type", sourceType);
    formData.append("file", file);

    setUploading(true);
    setUploadMessage(null);
    try {
      const data = await apiFetch("/documents/upload", {
        method: "POST",
        body: formData
      });
      if (data?.status === "duplicate") {
        setUploadMessage("Duplicate detected. This document is already uploaded.");
      } else {
        setUploadMessage("Upload queued successfully.");
      }
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      fetchDocuments();
      fetchEvents();
      setUploadTitleEdited(false);
    } catch (err: any) {
      setUploadMessage(err?.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleQuery = async () => {
    if (!tenantId) {
      setQueryError("Select a tenant before querying.");
      return;
    }
    if (!queryText.trim()) {
      setQueryError("Enter a question.");
      return;
    }
    const useHighlight = highlightText.trim().length > 0;
    setQuerying(true);
    setQueryError(null);
    setQueryAnswer("");
    setQueryCitations([]);
    try {
      const payload: any = {
        tenant_id: tenantId,
        session_id: sessionId,
        query_text: queryText
      };
      if (useSelectedOnly && selectedDocIds.length > 0) {
        payload.document_ids = selectedDocIds;
      }
      if (useHighlight) {
        payload.highlight_text = highlightText.trim();
        payload.highlight_mode = highlightMode;
      }
      const data: QueryResponse = await apiFetch("/query", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      setQueryAnswer(data.answer);
      setQueryCitations(data.citations || []);
      setNoAnswer(Boolean(data.no_answer));
    } catch (err: any) {
      setQueryError(err?.message || "Query failed.");
    } finally {
      setQuerying(false);
    }
  };

  const handleSendChat = async () => {
    if (!tenantId) {
      setChatError("Select a tenant before chatting.");
      return;
    }
    if (!activeSessionId) {
      setChatError("No active chat session.");
      return;
    }
    if (!chatInput.trim()) {
      setChatError("Enter a message.");
      return;
    }
    setChatError(null);
    setChatSending(true);
    const userMessage: ChatMessage = {
      id: `local-${Date.now()}`,
      session_id: activeSessionId,
      tenant_id: tenantId,
      user_id: "me",
      role: "user",
      content: chatInput.trim(),
      citations: []
    };
    setChatMessages((prev) => [...prev, userMessage]);
    const messageText = chatInput.trim();
    setChatInput("");
    try {
      const data = await apiFetch("/chat/messages", {
        method: "POST",
        body: JSON.stringify({
          tenant_id: tenantId,
          session_id: activeSessionId,
          message: messageText,
          document_ids: useSelectedOnly ? selectedDocIds : undefined,
          highlight_text: highlightText || undefined
        })
      });
      setChatMessages((prev) => [...prev, data]);
      await fetchChatSessions();
      fetchEvents();
      setHighlightText("");
    } catch (err: any) {
      setChatError(err?.message || "Chat failed.");
    } finally {
      setChatSending(false);
    }
  };

  const handleCreateChatSession = async () => {
    if (!tenantId) {
      setChatError("Select a tenant before creating a chat.");
      return;
    }
    setChatError(null);
    const title = "New Chat";
    try {
      const created = await apiFetch("/chat/sessions", {
        method: "POST",
        body: JSON.stringify({ tenant_id: tenantId, title })
      });
      setChatSessions((prev) => [created, ...prev]);
      setActiveSessionId(created.id);
      fetchEvents();
    } catch (err: any) {
      setChatError(err?.message || "Failed to create chat session.");
    }
  };

  const handleDeleteChatSession = async (sessionId: string) => {
    if (!tenantId) return;
    const ok = typeof window !== "undefined" ? window.confirm("Delete this chat session?") : false;
    if (!ok) return;
    try {
      await apiFetch(`/chat/sessions/${sessionId}`, { method: "DELETE" });
      const remaining = chatSessions.filter((session) => session.id !== sessionId);
      setChatSessions(remaining);
      if (activeSessionId === sessionId) {
        if (remaining.length) {
          setActiveSessionId(remaining[0].id);
        } else {
          setActiveSessionId("");
          setChatMessages([]);
        }
      }
      fetchEvents();
    } catch (err: any) {
      setChatError(err?.message || "Failed to delete chat.");
    }
  };

  const fetchPreview = async (documentId: string) => {
    if (!tenantId) return;
    setPreviewLoading(true);
    setPreviewDocId(documentId);
    try {
      const data: DocumentPreview = await apiFetch(
        `/documents/${documentId}/preview?tenant_id=${tenantId}`
      );
      setPreviewData(data);
    } catch (err) {
      setPreviewData(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!tenantId) {
      setSettingsMessage("Select a tenant first.");
      return;
    }
    setSettingsMessage(null);
    const payload: any = {
      tenant_id: tenantId,
      llm_provider: settingsState.llm_provider,
      embed_provider: settingsState.embed_provider,
      llm_model: settingsState.llm_model || null,
      embed_model: settingsState.embed_model || null,
      chunk_strategy_id: settingsState.chunk_strategy_id || null
    };
    if (openaiKeyInput.trim()) {
      payload.openai_api_key = openaiKeyInput.trim();
    }
    if (groqKeyInput.trim()) {
      payload.groq_api_key = groqKeyInput.trim();
    }
    if (latticeKeyInput.trim()) {
      payload.lattice_api_key = latticeKeyInput.trim();
    }
    try {
      const data = await apiFetch("/settings", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      setSettingsState({
        llm_provider: data.llm_provider || "custom",
        embed_provider: data.embed_provider || "custom",
        llm_model: data.llm_model || "",
        embed_model: data.embed_model || "",
        chunk_strategy_id: data.chunk_strategy_id || "",
        has_openai_key: Boolean(data.has_openai_key),
        has_groq_key: Boolean(data.has_groq_key),
        has_lattice_key: Boolean(data.has_lattice_key)
      });
      setOpenaiKeyInput("");
      setGroqKeyInput("");
      setLatticeKeyInput("");
      setSettingsMessage("Settings saved.");
    } catch (err: any) {
      setSettingsMessage(err?.message || "Failed to save settings.");
    }
  };

  const handleCreateTenant = async () => {
    if (!tenantNameInput.trim()) {
      setTenantCreateMessage("Enter a tenant name.");
      return;
    }
    setTenantCreateMessage(null);
    setTenantCreating(true);
    const slug = tenantSlugInput.trim() || slugify(tenantNameInput);
    try {
      const data = await apiFetch("/tenants", {
        method: "POST",
        body: JSON.stringify({ name: tenantNameInput.trim(), slug })
      });
      setTenants((prev) => [...prev, data]);
      setTenantId(data.id);
      setTenantNameInput("");
      setTenantSlugInput("");
      setTenantCreateMessage("Tenant created.");
      fetchEvents();
    } catch (err: any) {
      setTenantCreateMessage(err?.message || "Failed to create tenant.");
    } finally {
      setTenantCreating(false);
    }
  };

  const handleCreateUser = async () => {
    if (!newUserEmail.trim() || !newUserName.trim()) {
      setNewUserMessage("Provide name and email.");
      return;
    }
    setNewUserMessage(null);
    try {
      const data = await apiFetch("/users", {
        method: "POST",
        body: JSON.stringify({
          email: newUserEmail.trim(),
          name: newUserName.trim(),
          temp_password: newUserTempPassword.trim() || undefined
        })
      });
      setNewUserId(data.user_id);
      setNewUserLabel(`${newUserName} (${newUserEmail})`);
      setUserOptions((prev) => [
        { id: data.user_id, name: newUserName, email: newUserEmail },
        ...prev
      ]);
      setAssignUserId(data.user_id);
      setNewUserResetLink(data.reset_link);
      setNewUserEmail("");
      setNewUserName("");
      setNewUserTempPassword("");
      setNewUserMessage("User created. Copy the reset link.");
      fetchEvents();
    } catch (err: any) {
      setNewUserMessage(err?.message || "Failed to create user.");
    }
  };

  const handleAssignUser = async () => {
    if (!assignTenantId || !assignUserId) {
      setAssignMessage("Select tenant and provide user ID.");
      return;
    }
    setAssignMessage(null);
    setAssigning(true);
    try {
      await apiFetch(`/tenants/${assignTenantId}/members`, {
        method: "POST",
        body: JSON.stringify({ user_id: assignUserId, role: assignRole })
      });
      setAssignMessage("User assigned to tenant.");
      fetchEvents();
    } catch (err: any) {
      setAssignMessage(err?.message || "Failed to assign user.");
    } finally {
      setAssigning(false);
    }
  };


  const activeSession = chatSessions.find((session) => session.id === activeSessionId);
  const activeTenantName =
    tenants.find((tenant) => tenant.id === tenantId)?.name || (tenantId ? tenantId.slice(0, 8) : "No tenant");

  const formatEventTime = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleString();
  };

  const formatEvent = (event: ActivityEvent) => {
    const payload = event.payload || {};
    switch (event.event_type) {
      case "document_uploaded":
        return {
          title: "Document Uploaded",
          detail: payload.document_title || payload.document_id || "New document added"
        };
      case "ingestion_completed":
        return {
          title: "Ingestion Completed",
          detail: payload.document_title || payload.document_id || "Document indexed"
        };
      case "query_executed":
        return {
          title: "Query Executed",
          detail: payload.query_id ? `Query ${String(payload.query_id).slice(0, 8)}` : "Query run"
        };
      case "tenant_created":
        return {
          title: "Tenant Created",
          detail: payload.tenant_name || event.tenant_name || "New tenant"
        };
      case "tenant_member_added":
        return {
          title: "User Assigned",
          detail: payload.role ? `Role: ${payload.role}` : "User added to tenant"
        };
      case "user_created":
        return {
          title: "User Created",
          detail: payload.user_email || payload.user_name || "New user"
        };
      case "chat_session_created":
        return {
          title: "Chat Started",
          detail: payload.title || "New chat"
        };
      case "chat_session_deleted":
        return {
          title: "Chat Deleted",
          detail: "Session removed"
        };
      default:
        return {
          title: event.event_type.replace(/_/g, " "),
          detail: event.tenant_name || "Activity"
        };
    }
  };

  const dashboardEvents = activityEvents.filter((event) =>
    ["document_uploaded", "ingestion_completed", "chat_session_deleted"].includes(event.event_type)
  );

  const lastAssistantCitations =
    [...chatMessages]
      .reverse()
      .find((msg) => msg.role === "assistant" && msg.citations && msg.citations.length > 0)
      ?.citations ?? [];
  const navConfig = visibleNavItems.map((item) => ({
    label: item,
    path: navToRoute[item],
    icon: navIconComponents[item]
  }));

  const renderDashboard = () => (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Admin Portal"
        title="Dashboard"
        subtitle="A realtime pulse of your RAG operations and governance."
      />
      <div className="grid gap-4 lg:grid-cols-4">
        {[
          { label: "Active Tenants", value: orgMetrics?.total_tenants ?? "—" },
          { label: "Governed Users", value: orgMetrics?.total_users ?? "—" },
          { label: "Total Documents", value: orgMetrics?.total_documents ?? "—" },
          { label: "Monthly Queries", value: orgMetrics?.total_queries ?? "—" }
        ].map((metric) => (
          <div key={metric.label} className="card p-5 space-y-2">
            <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted)]">{metric.label}</div>
            <div className="text-2xl font-semibold">{metric.value}</div>
            <div className="h-1 rounded-full bg-[color:var(--accent-soft)]" />
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <div className="card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="font-display text-lg">Recent Activity</div>
            <span className="text-xs text-[color:var(--muted)]">Last 7 days</span>
          </div>
          <div className="space-y-3">
            {dashboardEvents.length === 0 && (
              <div className="text-sm text-[color:var(--muted)]">No recent activity yet.</div>
            )}
            {dashboardEvents.map((event) => {
              const formatted = formatEvent(event);
              return (
                <div
                  key={event.id}
                  className="flex items-center justify-between rounded-2xl bg-[color:var(--surface-muted)] p-4"
                >
                  <div>
                    <div className="font-semibold">{formatted.title}</div>
                    <div className="text-sm text-[color:var(--muted)]">{formatted.detail}</div>
                  </div>
                  <span className="text-xs text-[color:var(--muted)]">{formatEventTime(event.created_at)}</span>
                </div>
              );
            })}
          </div>
        </div>
        <div className="card p-6 space-y-4">
          <div className="font-display text-lg">Service Health</div>
          <div className="space-y-3">
            {[
              { label: "Vector Database", value: "Operational", status: "bg-emerald-500" },
              { label: "Indexing Queue", value: "Stable", status: "bg-emerald-500" },
              { label: "GPU Cluster", value: "90% Utilized", status: "bg-amber-400" }
            ].map((service) => (
              <div key={service.label} className="flex items-center justify-between rounded-2xl border border-[color:var(--border)] p-3">
                <div>
                  <div className="text-sm font-semibold">{service.label}</div>
                  <div className="text-xs text-[color:var(--muted)]">{service.value}</div>
                </div>
                <span className={`h-2.5 w-2.5 rounded-full ${service.status}`} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );

  const renderDocuments = () => (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Curation Workspace"
        title="Document Library"
        subtitle="Upload, organize, and monitor document ingestion across tenants."
        action={
          <button
            className="rounded-2xl bg-[color:var(--accent)] px-5 py-2 text-sm text-white shadow"
            onClick={() => fileInputRef.current?.click()}
          >
            Upload Document
          </button>
        }
      />
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-6">
          <div className="card p-6 space-y-4">
            <div className="text-sm font-semibold">New Upload</div>
            <div className="grid gap-4 md:grid-cols-2">
              <input
                className="w-full rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
                placeholder="Document title"
                value={uploadTitle}
                onChange={(e) => {
                  setUploadTitle(e.target.value);
                  setUploadTitleEdited(true);
                }}
              />
              <select
                className="w-full rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value)}
              >
                <option value="pdf">PDF</option>
                <option value="docx">DOCX</option>
                <option value="txt">TXT</option>
                <option value="html">HTML</option>
              </select>
              <select
                className="w-full rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
              >
                <option value="">Select tenant</option>
                {tenants.map((tenant) => (
                  <option key={tenant.id} value={tenant.id}>
                    {tenant.name}
                  </option>
                ))}
              </select>
            </div>
            <label className="block cursor-pointer rounded-2xl border-2 border-dashed border-[color:var(--border)] p-6 text-center">
              <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileChange} />
              <div className="text-sm text-[color:var(--muted)]">Drop files or click to browse</div>
              {selectedFiles.length > 0 && (
                <div className="mt-2 text-xs text-[color:var(--muted)]">
                  Selected: {selectedFiles.map((file) => file.name).join(", ")}
                </div>
              )}
            </label>
            <button
              className="w-full rounded-2xl bg-[color:var(--accent-strong)] px-5 py-2 text-sm text-white"
              onClick={handleUpload}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "Upload to Library"}
            </button>
            {uploadMessage && <div className="text-xs text-[color:var(--muted)]">{uploadMessage}</div>}
          </div>

          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="font-display text-lg">Recent Documents</div>
              <button className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]" onClick={fetchDocuments}>
                Refresh
              </button>
            </div>
            <div className="space-y-3">
              {documents.length === 0 && (
                <div className="text-sm text-[color:var(--muted)]">No documents uploaded yet.</div>
              )}
              {documents.slice(0, 6).map((doc) => (
                <div key={doc.id} className="flex items-center justify-between rounded-2xl border border-[color:var(--border)] p-4">
                  <div>
                    <div className="font-semibold">{doc.title}</div>
                    <div className="text-xs text-[color:var(--muted)]">
                      {doc.source_type.toUpperCase()} · {doc.status}
                    </div>
                  </div>
                  <button className="text-xs text-[color:var(--muted)] underline" onClick={() => fetchPreview(doc.id)}>
                    Preview
                  </button>
                </div>
              ))}
            </div>
          </div>
          {previewData && (
            <div className="card p-6 space-y-3">
              <div className="flex items-center justify-between">
                <div className="font-display text-lg">Preview</div>
                <button
                  className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]"
                  onClick={() => setPreviewData(null)}
                >
                  Close
                </button>
              </div>
              <div className="text-xs text-[color:var(--muted)]">
                {previewLoading ? "Loading preview..." : previewData.title}
              </div>
              <div className="max-h-[280px] overflow-auto rounded-2xl border border-[color:var(--border)] p-4 text-sm">
                {previewData.preview_text || "No preview available yet."}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="card p-6 space-y-4">
            <div className="font-display text-lg">Library Stats</div>
            {[
              { label: "Total Files", value: documents.length },
              { label: "Active Tenant", value: activeTenantName },
              { label: "Index Status", value: documents.length ? "Healthy" : "Waiting" }
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between rounded-2xl bg-[color:var(--surface-muted)] p-3">
                <div className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">{item.label}</div>
                <div className="text-sm font-semibold">{item.value}</div>
              </div>
            ))}
          </div>
          <div className="card p-6 space-y-4">
            <div className="font-display text-lg">Recent Actions</div>
            <div className="space-y-3 text-sm text-[color:var(--muted)]">
              <div>• Policy: Auto-index enabled</div>
              <div>• Last crawl: 28 minutes ago</div>
              <div>• Pending uploads: {Math.max(0, documents.length - 4)}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );

  const renderOrganization = () => (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Admin Portal"
        title="Organization Management"
        subtitle="Manage tenants, governance, and organization-wide access."
      />
      <div className="grid gap-4 lg:grid-cols-3">
        {[
          { label: "Active Tenants", value: orgMetrics?.total_tenants ?? "—" },
          { label: "Governed Users", value: orgMetrics?.total_users ?? "—" },
          { label: "Resource Utilization", value: "84%" }
        ].map((metric) => (
          <div key={metric.label} className="card p-5 space-y-2">
            <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted)]">{metric.label}</div>
            <div className="text-2xl font-semibold">{metric.value}</div>
          </div>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="card p-6 space-y-4">
          <div className="font-display text-lg">Tenants</div>
          <div className="grid gap-4 md:grid-cols-2">
            {tenants.length === 0 ? (
              <div className="text-sm text-[color:var(--muted)]">No tenants available.</div>
            ) : (
              tenants.map((tenant) => (
                <div key={tenant.id} className="rounded-2xl border border-[color:var(--border)] p-4">
                  <div className="font-semibold">{tenant.name}</div>
                  <div className="text-xs text-[color:var(--muted)]">{tenant.slug}</div>
                </div>
              ))
            )}
          </div>
        </div>
        <div className="card p-6 space-y-4">
          <div className="font-display text-lg">Governance Log</div>
          <div className="space-y-3 text-sm text-[color:var(--muted)]">
            <div>• Tenant Created · Stellar Tech</div>
            <div>• User Migration · 12 users moved</div>
            <div>• Quota Alert · 90% storage reached</div>
          </div>
        </div>
      </div>
      {isOrgAdmin && (
        <div className="card p-6 space-y-4">
          <div className="font-display text-lg">Create Tenant</div>
          <div className="grid gap-4 md:grid-cols-2">
            <input
              className="w-full rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
              placeholder="Tenant name"
              value={tenantNameInput}
              onChange={(e) => {
                setTenantNameInput(e.target.value);
                if (!tenantSlugInput.trim()) {
                  setTenantSlugInput(slugify(e.target.value));
                }
              }}
            />
            <input
              className="w-full rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
              placeholder="Tenant slug"
              value={tenantSlugInput}
              onChange={(e) => setTenantSlugInput(e.target.value)}
            />
          </div>
          {tenantCreateMessage && <div className="text-xs text-[color:var(--muted)]">{tenantCreateMessage}</div>}
          <button
            className="rounded-2xl bg-[color:var(--accent-strong)] px-5 py-2 text-sm text-white"
            onClick={handleCreateTenant}
            disabled={tenantCreating}
          >
            {tenantCreating ? "Creating..." : "Create Tenant"}
          </button>
        </div>
      )}
    </section>
  );

  const renderUsage = () => (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Admin Portal"
        title="Usage"
        subtitle="Monitor token consumption and infrastructure efficiency."
      />
      <div className="grid gap-4 lg:grid-cols-3">
        {[
          { label: "Total Tokens", value: "1.2B" },
          { label: "Avg. Latency", value: "240ms" },
          { label: "Storage Used", value: "4.2 TB" }
        ].map((metric) => (
          <div key={metric.label} className="card p-5 space-y-2">
            <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted)]">{metric.label}</div>
            <div className="text-2xl font-semibold">{metric.value}</div>
            <div className="h-1 rounded-full bg-[color:var(--accent-soft)]" />
          </div>
        ))}
      </div>
      <div className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="font-display text-lg">Query Volume Over Time</div>
          <span className="text-xs text-[color:var(--muted)]">Last 5 days</span>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sampleAnalytics}>
              <XAxis dataKey="name" stroke="currentColor" />
              <YAxis stroke="currentColor" />
              <Tooltip />
              <Line type="monotone" dataKey="queries" stroke="var(--accent)" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );

  const renderUserManagement = () => (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Admin Portal"
        title="User Management"
        subtitle="Provision new identities and assign tenant roles."
      />
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-6">
          <div className="card p-6 space-y-4">
            <div className="font-display text-lg">Create New User</div>
            <div className="grid gap-4 md:grid-cols-2">
              <input
                className="w-full rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
                placeholder="Full name"
                value={newUserName}
                onChange={(e) => setNewUserName(e.target.value)}
              />
              <input
                className="w-full rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
                placeholder="Corporate email"
                value={newUserEmail}
                onChange={(e) => setNewUserEmail(e.target.value)}
              />
            </div>
            <input
              className="w-full rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
              placeholder="Temporary password (optional)"
              value={newUserTempPassword}
              onChange={(e) => setNewUserTempPassword(e.target.value)}
            />
            {newUserResetLink && (
              <div className="rounded-2xl bg-[color:var(--surface-muted)] p-3 text-xs break-all">
                Reset link:{" "}
                <a
                  href={newUserResetLink}
                  className="underline text-[color:var(--accent)]"
                  target="_blank"
                  rel="noreferrer"
                >
                  {newUserResetLink}
                </a>
              </div>
            )}
            {newUserMessage && <div className="text-xs text-[color:var(--muted)]">{newUserMessage}</div>}
            <button
              className="rounded-2xl bg-[color:var(--accent-strong)] px-5 py-2 text-sm text-white"
              onClick={handleCreateUser}
            >
              Create User & Generate Link
            </button>
          </div>

          <div className="card p-6 space-y-4">
            <div className="font-display text-lg">Assign User to Tenant</div>
            <div className="grid gap-4 md:grid-cols-3">
              <select
                className="w-full rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
                value={assignTenantId}
                onChange={(e) => setAssignTenantId(e.target.value)}
              >
                <option value="">Select tenant</option>
                {tenants.map((tenant) => (
                  <option key={tenant.id} value={tenant.id}>
                    {tenant.name}
                  </option>
                ))}
              </select>
              <select
                className="w-full rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
                value={assignUserId}
                onChange={(e) => setAssignUserId(e.target.value)}
              >
                <option value="">Select user</option>
                {userOptions.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.name} ({user.email})
                  </option>
                ))}
              </select>
              <select
                className="w-full rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
                value={assignRole}
                onChange={(e) => setAssignRole(e.target.value)}
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
                <option value="owner">Owner</option>
              </select>
            </div>
            {assignMessage && <div className="text-xs text-[color:var(--muted)]">{assignMessage}</div>}
            <button
              className="rounded-2xl bg-[color:var(--accent)] px-5 py-2 text-sm text-white"
              onClick={handleAssignUser}
              disabled={assigning}
            >
              {assigning ? "Assigning..." : "Confirm Assignment"}
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card p-6 space-y-3">
            <div className="font-display text-lg">Provisioning Policy</div>
            <div className="text-sm text-[color:var(--muted)]">All new users start with zero-trust permissions.</div>
            <div className="text-sm text-[color:var(--muted)]">Setup links expire after 24 hours.</div>
            <div className="text-sm text-[color:var(--muted)]">Provisioning actions are audited.</div>
          </div>
          <div className="card p-6 space-y-4">
            <div className="font-display text-lg">Need Bulk Import?</div>
            <div className="text-sm text-[color:var(--muted)]">
              Import multiple users at once via CSV or directory sync.
            </div>
            <button className="rounded-2xl bg-[color:var(--accent)] px-5 py-2 text-sm text-white">
              Open Data Importer
            </button>
          </div>
        </div>
      </div>
    </section>
  );

  const renderChat = () => (
    <section className="flex h-full flex-col">
      <div className="grid h-full gap-4 lg:grid-cols-[260px_2fr_1fr]">
        <aside className="card h-full p-4 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted)]">Chat History</div>
            <button
              className="rounded-full border border-[color:var(--border)] px-3 py-1 text-xs text-[color:var(--muted)]"
              onClick={handleCreateChatSession}
            >
              New
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            <div className="flex min-h-full flex-col gap-2 justify-start">
            {chatSessions.length === 0 && (
              <div className="text-sm text-[color:var(--muted)]">No chats yet.</div>
            )}
            {chatSessions.map((session) => (
              <div
                key={session.id}
                className={`flex items-center justify-between gap-2 rounded-2xl px-3 py-2 text-sm transition ${
                  activeSessionId === session.id
                    ? "bg-[color:var(--accent)] text-white"
                    : "border border-[color:var(--border)] text-[color:var(--muted-strong)]"
                }`}
              >
                <button
                  className="flex-1 text-left"
                  onClick={() => setActiveSessionId(session.id)}
                >
                  {session.title || "Chat"}
                </button>
                <button
                  className="h-7 w-7 rounded-full border border-[color:var(--border)] text-[color:var(--muted)] hover:text-[color:var(--accent)]"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteChatSession(session.id);
                  }}
                  title="Delete chat"
                >
                  <Trash2 className="mx-auto h-3 w-3" />
                </button>
              </div>
            ))}
            </div>
          </div>
        </aside>

        <div className="card h-full px-5 pt-5 pb-3 flex flex-col gap-3 overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">Tenant</span>
              {isOrgAdmin ? (
                <select
                  className="rounded-2xl border border-[color:var(--border)] bg-transparent p-2 text-sm"
                  value={tenantId}
                  onChange={(e) => setTenantId(e.target.value)}
                >
                  <option value="">Select tenant</option>
                  {tenants.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>
                      {tenant.name}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="rounded-full bg-[color:var(--accent-soft)] px-3 py-1 text-xs text-[color:var(--muted)]">
                  {activeTenantName}
                </span>
              )}
            </div>
            <div className="text-xs text-[color:var(--muted)]">
              Session: <span className="font-semibold text-[color:var(--text)]">{activeSession?.title || "None"}</span>
            </div>
          </div>

          <div ref={chatScrollRef} className="flex-1 overflow-y-auto pr-2">
            <div className="rounded-2xl bg-[color:var(--surface-muted)] p-4 text-sm text-[color:var(--muted)]">
              Hello! I've analyzed your enterprise documents. How can I assist you today?
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {["Summarize Q3 revenue", "Explain quantum specs", "Locate cooling requirements"].map((prompt) => (
                <button
                  key={prompt}
                  className="rounded-full border border-[color:var(--border)] px-3 py-1 text-xs text-[color:var(--muted)]"
                  onClick={() => setChatInput(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>

            <div className="mt-4 space-y-4">
              {chatMessages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                      msg.role === "user"
                        ? "bg-[color:var(--accent)] text-white"
                        : "bg-[color:var(--surface-muted)] text-[color:var(--text)]"
                    }`}
                  >
                    <div className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)] mb-1">
                      {msg.role === "user" ? "You" : "Assistant"}
                    </div>
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {chatError && <div className="text-xs text-red-500">{chatError}</div>}

          <div className="border-t border-[color:var(--border)] pt-2 pb-1">
            <div className="flex items-center gap-3">
              <input
                className="flex-1 rounded-2xl border border-[color:var(--border)] bg-transparent p-3"
                placeholder="Ask anything about your data..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendChat();
                  }
                }}
              />
              <button
                className="rounded-2xl bg-[color:var(--accent-strong)] px-5 py-2 text-sm text-white"
                onClick={handleSendChat}
                disabled={chatSending}
              >
                {chatSending ? "Sending..." : "Send"}
              </button>
            </div>
          </div>
        </div>

        <aside className="flex h-full flex-col gap-4">
          <div className="card flex-1 p-5 space-y-4 overflow-y-auto">
            <div className="font-display text-lg">Document Citations</div>
            {lastAssistantCitations.length === 0 ? (
              <div className="text-sm text-[color:var(--muted)]">No citations yet.</div>
            ) : (
              <div className="space-y-3">
                {lastAssistantCitations.slice(0, 3).map((citation) => (
                  <div key={citation.chunk_id} className="rounded-2xl border border-[color:var(--border)] p-3 text-xs">
                    <div className="font-semibold">Source {citation.document_id.slice(0, 8)}</div>
                    <div className="text-[color:var(--muted)]">{citation.text.slice(0, 120)}...</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card flex-1 p-5 space-y-4 overflow-y-auto">
            <div className="font-display text-lg">Documents in Scope</div>
            <div className="space-y-2">
              {documents.length === 0 && (
                <div className="text-sm text-[color:var(--muted)]">No documents available.</div>
              )}
              {documents.slice(0, 6).map((doc) => (
                <label
                  key={doc.id}
                  className={`flex items-center gap-2 rounded-2xl border p-2 text-xs ${
                    selectedDocIds.includes(doc.id)
                      ? "border-[color:var(--accent)] bg-[color:var(--accent-soft)]"
                      : "border-[color:var(--border)]"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedDocIds.includes(doc.id)}
                    onChange={(e) => {
                      const checked = e.target.checked;
                      setSelectedDocIds((prev) => (checked ? [...prev, doc.id] : prev.filter((id) => id !== doc.id)));
                    }}
                  />
                  <span className="truncate">{doc.title}</span>
                </label>
              ))}
            </div>
            <label className="flex items-center gap-2 text-xs text-[color:var(--muted)]">
              <input
                type="checkbox"
                checked={useSelectedOnly}
                onChange={(e) => setUseSelectedOnly(e.target.checked)}
              />
              Use selected documents only
            </label>
          </div>
        </aside>
      </div>
    </section>
  );

  if (!authed) {
    return (
      <div className="min-h-screen p-6 flex items-center justify-center">
        <div className="card p-8 w-full max-w-md space-y-6">
          <div className="text-center">
            <h1 className="font-display text-2xl">Welcome to CitadelRAG</h1>
            <p className="text-sm text-[color:var(--muted)]">Login with admin/admin or create an account.</p>
          </div>
          <AuthForm mode={authMode} onAuthSuccess={() => setAuthed(true)} />
          <button
            className="text-sm text-[color:var(--muted)] underline"
            onClick={() => setAuthMode(authMode === "login" ? "signup" : "login")}
          >
            {authMode === "login" ? "Need an account? Sign up" : "Already have an account? Log in"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[color:var(--bg)]">
      <div className="flex h-screen gap-4 p-4">
        <SidebarNav
          items={navConfig}
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((prev) => !prev)}
          onLogout={() => {
            localStorage.removeItem("access_token");
            setAuthed(false);
          }}
          theme={theme}
          onThemeToggle={() => setTheme(theme === "light" ? "dark" : "light")}
        />
        <div className="flex-1 overflow-y-auto pr-2">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={renderDashboard()} />
            <Route path="/documents" element={renderDocuments()} />
            <Route path="/organization" element={renderOrganization()} />
            <Route path="/usage" element={renderUsage()} />
            <Route path="/user-management" element={renderUserManagement()} />
            <Route path="/chat" element={renderChat()} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
