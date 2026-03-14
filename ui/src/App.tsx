import { useEffect, useRef, useState } from "react";
import {
  MessageSquare,
  FileText,
  BarChart3,
  Settings as SettingsIcon,
  Building2,
  ClipboardList
} from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import AuthForm, { AuthMode } from "./components/AuthForm";
import { apiFetch } from "./lib/api";

const navItems = ["Chat", "Documents", "Evaluations", "Analytics", "Settings", "Organization"] as const;

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
  const [active, setActive] = useState<NavItem>("Chat");
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
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatSending, setChatSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatTitleInput, setChatTitleInput] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [useSelectedOnly, setUseSelectedOnly] = useState<boolean>(false);
  const [sessionId] = useState<string>(() =>
    typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}`
  );
  const [previewDocId, setPreviewDocId] = useState<string>("");
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<DocumentPreview | null>(null);
  const [previewExpanded, setPreviewExpanded] = useState(false);
  const [rightPanelWidth, setRightPanelWidth] = useState(420);
  const resizingRef = useRef(false);
  const [highlightText, setHighlightText] = useState<string>("");
  const [highlightMode, setHighlightMode] = useState<"highlight_only" | "highlight_plus_docs">("highlight_only");

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
    : navItems.filter((item) => !["Organization", "Settings", "Analytics", "Evaluations"].includes(item));

  const navIconComponents: Record<NavItem, JSX.Element> = {
    Chat: <MessageSquare className="h-4 w-4" />,
    Documents: <FileText className="h-4 w-4" />,
    Evaluations: <ClipboardList className="h-4 w-4" />,
    Analytics: <BarChart3 className="h-4 w-4" />,
    Settings: <SettingsIcon className="h-4 w-4" />,
    Organization: <Building2 className="h-4 w-4" />
  };

  const slugify = (value: string) =>
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)+/g, "");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!isOrgAdmin && ["Organization", "Settings", "Analytics", "Evaluations"].includes(active)) {
      setActive("Chat");
    }
  }, [isOrgAdmin, active]);

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
        setActiveSessionId(data[0].id);
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
    const title = chatTitleInput.trim() || "New Chat";
    try {
      const created = await apiFetch("/chat/sessions", {
        method: "POST",
        body: JSON.stringify({ tenant_id: tenantId, title })
      });
      setChatSessions((prev) => [created, ...prev]);
      setActiveSessionId(created.id);
      setChatTitleInput("");
    } catch (err: any) {
      setChatError(err?.message || "Failed to create chat session.");
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
      setPreviewExpanded(true);
    } catch (err) {
      setPreviewData(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  useEffect(() => {
    const handleMove = (event: MouseEvent) => {
      if (!resizingRef.current) return;
      const maxWidth = Math.min(900, window.innerWidth - 200);
      const newWidth = Math.min(maxWidth, Math.max(280, window.innerWidth - event.clientX - 24));
      setRightPanelWidth(newWidth);
    };
    const handleUp = () => {
      resizingRef.current = false;
    };
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
    };
  }, []);

  const handleHighlightMouseUp = () => {
    const selection = window.getSelection();
    const text = selection?.toString() || "";
    if (text.trim().length >= 20) {
      setHighlightText(text.trim());
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
    } catch (err: any) {
      setAssignMessage(err?.message || "Failed to assign user.");
    } finally {
      setAssigning(false);
    }
  };


  const activeSession = chatSessions.find((session) => session.id === activeSessionId);
  const activeTenantName =
    tenants.find((tenant) => tenant.id === tenantId)?.name || (tenantId ? tenantId.slice(0, 8) : "No tenant");

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
    <div className="h-screen p-4">
      <div
        className={`w-full h-full grid grid-cols-1 gap-6 ${
          sidebarCollapsed ? "lg:grid-cols-[72px_1fr]" : "lg:grid-cols-[260px_1fr]"
        }`}
      >
        <aside className={`card p-4 space-y-6 fade-in ${sidebarCollapsed ? "items-center" : ""}`}>
          <div className="flex items-start justify-between">
            {sidebarCollapsed && (
              <div className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">CR</div>
            )}
            <button
              className="ml-2 h-6 w-6 rounded-full border border-[color:var(--border)] text-[color:var(--muted)] hover:text-white hover:bg-[color:var(--accent)] flex items-center justify-center"
              onClick={() => setSidebarCollapsed((prev) => !prev)}
              title={sidebarCollapsed ? "Expand" : "Collapse"}
            >
              {sidebarCollapsed ? "›" : "‹"}
            </button>
          </div>
          <div className="space-y-2">
            {visibleNavItems.map((item) => (
              <button
                key={item}
                onClick={() => setActive(item)}
                className={`w-full text-left px-4 py-2 rounded-xl transition flex items-center gap-3 ${
                  active === item
                    ? "bg-[color:var(--accent)] text-white"
                    : "hover:bg-[color:var(--bg-secondary)]"
                }`}
              >
                <span className="flex items-center justify-center">
                  {navIconComponents[item]}
                </span>
                {!sidebarCollapsed && <span>{item}</span>}
              </button>
            ))}
          </div>
          <div className="flex items-center justify-between">
            {!sidebarCollapsed && (
              <span className="text-sm text-[color:var(--muted)]">Theme</span>
            )}
            <button
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
              className="badge"
            >
              {theme === "light" ? "Dark" : "Light"}
            </button>
          </div>
          <button
            className="text-sm text-[color:var(--muted)] underline"
            onClick={() => {
              localStorage.removeItem("access_token");
              setAuthed(false);
            }}
          >
            {sidebarCollapsed ? "Out" : "Log out"}
          </button>
        </aside>

        <main className="h-full flex flex-col gap-6 overflow-hidden">
          <header className="card p-6 fade-in space-y-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-[color:var(--accent)] text-white flex items-center justify-center text-sm font-semibold">
                CR
              </div>
              <div>
                <div className="font-display text-lg">CitadelRAG</div>
                <div className="text-xs text-[color:var(--muted)]">Knowledge Control Room</div>
              </div>
            </div>
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h2 className="font-display text-3xl">{active}</h2>
                <p className="text-[color:var(--muted)]">
                  Manage documents, run queries, evaluate retrieval, and monitor usage.
                </p>
              </div>
            </div>
          </header>

          {active === "Documents" && (
            <section className="card p-6 fade-in space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-display text-xl">Upload Documents</h3>
                <div className="flex items-center gap-2">
                  <span className="badge">Accepted: PDF, DOCX, TXT, HTML</span>
                  <button
                    className="badge"
                    onClick={fetchDocuments}
                  >
                    Refresh
                  </button>
                </div>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <input
                  className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                  placeholder="Document title"
                  value={uploadTitle}
                  onChange={(e) => {
                    setUploadTitle(e.target.value);
                    setUploadTitleEdited(true);
                  }}
                />
                <select
                  className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                >
                  <option value="pdf">PDF</option>
                  <option value="docx">DOCX</option>
                  <option value="txt">TXT</option>
                  <option value="html">HTML</option>
                </select>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <select
                  className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
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
              <label
                className="border-2 border-dashed border-[color:var(--border)] rounded-2xl p-8 text-center block cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  onChange={handleFileChange}
                />
                <p className="text-[color:var(--muted)]">Drop files here or click to upload.</p>
                <button
                  type="button"
                  className="mt-4 px-4 py-2 rounded-xl bg-[color:var(--accent)] text-white inline-flex items-center justify-center"
                  onClick={(event) => {
                    event.preventDefault();
                    fileInputRef.current?.click();
                  }}
                >
                  Choose File
                </button>
                {selectedFiles.length > 0 && (
                  <div className="mt-3 text-sm text-[color:var(--muted)]">
                    Selected: {selectedFiles.map((file) => file.name).join(", ")}
                  </div>
                )}
              </label>
              <button
                className="w-full px-6 py-2 rounded-xl bg-[color:var(--accent-strong)] text-white"
                onClick={handleUpload}
                disabled={uploading}
              >
                {uploading ? "Uploading..." : "Upload"}
              </button>
              {uploadMessage && (
                <div className="text-sm text-[color:var(--muted)]">{uploadMessage}</div>
              )}
              <div className="grid md:grid-cols-2 gap-4">
                {documents.length === 0 && (
                  <div className="text-sm text-[color:var(--muted)]">
                    No documents yet. Upload one to get started.
                  </div>
                )}
                {documents.map((doc) => (
                  <div key={doc.id} className="p-4 rounded-xl bg-[color:var(--bg-secondary)] space-y-1">
                    <div className="font-semibold">{doc.title}</div>
                    <div className="text-sm text-[color:var(--muted)]">
                      Status: {doc.status} · Type: {doc.source_type}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {active === "Chat" && (
            <section
              className="grid gap-6 flex-1 min-h-0"
              style={{ gridTemplateColumns: `1fr ${rightPanelWidth}px` }}
            >
              <div className="card p-6 pb-8 fade-in space-y-4 h-full flex flex-col min-h-0">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">Tenant</span>
                    {isOrgAdmin ? (
                      <select
                        className="p-2 rounded-xl border border-[color:var(--border)] bg-transparent text-sm"
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
                      <span className="badge">{activeTenantName}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">Session</span>
                    <span className="badge">{activeSession?.title || "None"}</span>
                    <span className="badge">Total: {chatSessions.length}</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <input
                      className="flex-1 p-2 rounded-xl border border-[color:var(--border)] bg-transparent text-sm"
                      placeholder="New chat title"
                      value={chatTitleInput}
                      onChange={(e) => setChatTitleInput(e.target.value)}
                    />
                    <button
                      className="px-3 py-2 rounded-xl bg-[color:var(--accent)] text-white text-sm"
                      onClick={handleCreateChatSession}
                    >
                      New
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {chatSessions.map((session) => (
                      <button
                        key={session.id}
                        onClick={() => setActiveSessionId(session.id)}
                        className={`px-3 py-1 rounded-full text-sm border ${
                          activeSessionId === session.id
                            ? "border-[color:var(--accent-strong)] bg-[color:var(--accent)] text-white"
                            : "border-[color:var(--border)] text-[color:var(--muted)]"
                        }`}
                      >
                        {session.title || "Chat"}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex flex-col gap-4 flex-1 overflow-y-auto">
                  {chatMessages.length === 0 && (
                    <div className="text-sm text-[color:var(--muted)]">
                      Ask a question to start chatting.
                    </div>
                  )}
                  {chatMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-sm ${
                          msg.role === "user"
                            ? "bg-[color:var(--accent)] text-white"
                            : "bg-[color:var(--bg-secondary)]"
                        }`}
                      >
                        <div className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)] mb-1">
                          {msg.role === "user" ? "You" : "Assistant"}
                        </div>
                        <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                        {msg.citations && msg.citations.length > 0 && msg.role === "assistant" && (
                          <div className="mt-2 text-xs text-[color:var(--muted)]">
                            {msg.citations.length} citations
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                {chatError && <div className="text-sm text-red-500">{chatError}</div>}
                {highlightText.trim().length > 0 && (
                  <div className="flex items-center justify-between gap-3 rounded-xl border border-[color:var(--border)] bg-[color:var(--bg-secondary)] px-4 py-2 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="uppercase tracking-[0.2em] text-[color:var(--muted)]">Highlight</span>
                      <span className="text-[color:var(--muted)]">
                        {highlightText.trim().slice(0, 140)}
                        {highlightText.trim().length > 140 ? "…" : ""}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="text-xs underline text-[color:var(--muted)]"
                      onClick={() => setHighlightText("")}
                    >
                      Clear
                    </button>
                  </div>
                )}
                <div className="flex items-center gap-3 pt-2">
                  <input
                    className="flex-1 p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                    placeholder="Ask about your documents..."
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                  />
                  <button
                    className="px-6 py-2 rounded-xl bg-[color:var(--accent-strong)] text-white"
                    onClick={handleSendChat}
                    disabled={chatSending}
                  >
                    {chatSending ? "Sending..." : "Send"}
                  </button>
                </div>
                <label className="flex items-center gap-2 text-sm text-[color:var(--muted)]">
                  <input
                    type="checkbox"
                    checked={useSelectedOnly}
                    onChange={(e) => setUseSelectedOnly(e.target.checked)}
                  />
                  Use selected documents only
                </label>
              </div>

              <aside className="card p-6 fade-in space-y-4 h-full flex flex-col relative">
                <div
                  className="absolute -left-2 top-0 bottom-0 w-2 cursor-col-resize"
                  onMouseDown={() => {
                    resizingRef.current = true;
                  }}
                  title="Drag to resize"
                />
                <div className="flex items-center justify-between">
                  <h4 className="font-display text-lg">Documents</h4>
                  {isOrgAdmin ? (
                    <select
                      className="p-2 rounded-xl border border-[color:var(--border)] bg-transparent text-sm"
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
                    <span className="badge">{tenantId ? tenantId.slice(0, 8) : "No tenant"}</span>
                  )}
                </div>
                <div className="space-y-2 flex-1 overflow-y-auto">
                  {documents.length === 0 && (
                    <div className="text-sm text-[color:var(--muted)]">No documents uploaded yet.</div>
                  )}
                  {documents.map((doc) => (
                    <label
                      key={doc.id}
                      className={`flex items-center gap-2 p-2 rounded-xl border ${
                        selectedDocIds.includes(doc.id)
                          ? "border-[color:var(--accent-strong)]"
                          : "border-[color:var(--border)]"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedDocIds.includes(doc.id)}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setSelectedDocIds((prev) =>
                            checked ? [...prev, doc.id] : prev.filter((id) => id !== doc.id)
                          );
                        }}
                      />
                      <button
                        type="button"
                        className="text-left text-sm underline text-[color:var(--muted)]"
                        onClick={() => fetchPreview(doc.id)}
                      >
                        {doc.title}
                      </button>
                    </label>
                  ))}
                </div>

                {previewData && (
                  <div className="border-t border-[color:var(--border)] pt-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-semibold">Preview</div>
                      <button
                        className="text-xs underline text-[color:var(--muted)]"
                        onClick={() => setPreviewExpanded((prev) => !prev)}
                      >
                        {previewExpanded ? "Collapse" : "Expand"}
                      </button>
                    </div>
                    <div
                      className={`text-sm whitespace-pre-wrap border border-[color:var(--border)] rounded-xl p-3 bg-transparent ${
                        previewExpanded ? "max-h-[60vh]" : "max-h-[30vh]"
                      } overflow-auto`}
                      onMouseUp={handleHighlightMouseUp}
                    >
                      {previewData.preview_text || "No preview available yet."}
                    </div>
                  </div>
                )}

                <div className="pt-2 border-t border-[color:var(--border)] space-y-3">
                  <div className="text-sm text-[color:var(--muted)]">Upload document</div>
                  <input
                    className="w-full p-2 rounded-xl border border-[color:var(--border)] bg-transparent text-sm"
                    placeholder="Document title"
                    value={uploadTitle}
                    onChange={(e) => {
                      setUploadTitle(e.target.value);
                      setUploadTitleEdited(true);
                    }}
                  />
                  <select
                    className="w-full p-2 rounded-xl border border-[color:var(--border)] bg-transparent text-sm"
                    value={sourceType}
                    onChange={(e) => setSourceType(e.target.value)}
                  >
                    <option value="pdf">PDF</option>
                    <option value="docx">DOCX</option>
                    <option value="txt">TXT</option>
                    <option value="html">HTML</option>
                  </select>
                  <button
                    type="button"
                    className="w-full px-3 py-2 rounded-xl bg-[color:var(--accent)] text-white"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Choose File
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                  <button
                    className="w-full px-3 py-2 rounded-xl bg-[color:var(--accent-strong)] text-white"
                    onClick={handleUpload}
                    disabled={uploading}
                  >
                    {uploading ? "Uploading..." : "Upload"}
                  </button>
                  {uploadMessage && (
                    <div className="text-xs text-[color:var(--muted)]">{uploadMessage}</div>
                  )}
                </div>
              </aside>
            </section>
          )}

          {active === "Evaluations" && (
            <section className="card p-6 fade-in space-y-4">
              <h3 className="font-display text-xl">Evaluation Runs</h3>
              <div className="grid md:grid-cols-3 gap-4">
                {['Recall@5', 'MRR', 'nDCG@5'].map((metric) => (
                  <div key={metric} className="p-4 rounded-xl bg-[color:var(--bg-secondary)]">
                    <div className="text-sm text-[color:var(--muted)]">{metric}</div>
                    <div className="text-2xl font-semibold">0.78</div>
                  </div>
                ))}
              </div>
              <button className="px-6 py-2 rounded-xl bg-[color:var(--accent)] text-white">
                Run Evaluation
              </button>
            </section>
          )}

          {active === "Analytics" && (
            <section className="card p-6 fade-in space-y-4">
              <h3 className="font-display text-xl">Usage Analytics</h3>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-[color:var(--bg-secondary)]">
                  <div className="text-sm text-[color:var(--muted)]">Query Volume</div>
                  <div className="text-2xl font-semibold">740</div>
                </div>
                <div className="p-4 rounded-xl bg-[color:var(--bg-secondary)]">
                  <div className="text-sm text-[color:var(--muted)]">Avg Latency</div>
                  <div className="text-2xl font-semibold">1.4s</div>
                </div>
                <div className="p-4 rounded-xl bg-[color:var(--bg-secondary)]">
                  <div className="text-sm text-[color:var(--muted)]">No-Answer Rate</div>
                  <div className="text-2xl font-semibold">6%</div>
                </div>
              </div>
              <div className="h-60 bg-[color:var(--bg-secondary)] rounded-xl p-4">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={sampleAnalytics}>
                    <XAxis dataKey="name" stroke="currentColor" />
                    <YAxis stroke="currentColor" />
                    <Tooltip />
                    <Line type="monotone" dataKey="queries" stroke="var(--accent-strong)" strokeWidth={3} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          )}

          {active === "Settings" && (
            <section className="card p-6 fade-in space-y-4">
              <h3 className="font-display text-xl">Settings</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <div className="text-sm text-[color:var(--muted)]">LLM Provider</div>
                  <select
                    className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                    value={settingsState.llm_provider}
                    onChange={(e) =>
                      setSettingsState({ ...settingsState, llm_provider: e.target.value })
                    }
                  >
                    <option value="groq">Groq</option>
                    <option value="openai">OpenAI</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
                <div className="space-y-3">
                  <div className="text-sm text-[color:var(--muted)]">LLM Model</div>
                  <input
                    className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                    placeholder="e.g. llama-3.1-70b"
                    value={settingsState.llm_model}
                    onChange={(e) =>
                      setSettingsState({ ...settingsState, llm_model: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-3">
                  <div className="text-sm text-[color:var(--muted)]">Embedding Provider</div>
                  <select
                    className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                    value={settingsState.embed_provider}
                    onChange={(e) =>
                      setSettingsState({ ...settingsState, embed_provider: e.target.value })
                    }
                  >
                    <option value="openai">OpenAI</option>
                    <option value="huggingface">HuggingFace</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
                <div className="space-y-3">
                  <div className="text-sm text-[color:var(--muted)]">Embedding Model</div>
                  <input
                    className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                    placeholder="e.g. text-embedding-3-large"
                    value={settingsState.embed_model}
                    onChange={(e) =>
                      setSettingsState({ ...settingsState, embed_model: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-3">
                  <div className="text-sm text-[color:var(--muted)]">OpenAI API Key</div>
                  <input
                    className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                    placeholder={settingsState.has_openai_key ? "Saved (enter to replace)" : "Enter OpenAI key"}
                    type="password"
                    value={openaiKeyInput}
                    onChange={(e) => setOpenaiKeyInput(e.target.value)}
                  />
                </div>
                <div className="space-y-3">
                  <div className="text-sm text-[color:var(--muted)]">Groq API Key</div>
                  <input
                    className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                    placeholder={settingsState.has_groq_key ? "Saved (enter to replace)" : "Enter Groq key"}
                    type="password"
                    value={groqKeyInput}
                    onChange={(e) => setGroqKeyInput(e.target.value)}
                  />
                </div>
                <div className="space-y-3">
                  <div className="text-sm text-[color:var(--muted)]">Lattice API Key</div>
                  <input
                    className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                    placeholder={settingsState.has_lattice_key ? "Saved (enter to replace)" : "Enter Lattice key"}
                    type="password"
                    value={latticeKeyInput}
                    onChange={(e) => setLatticeKeyInput(e.target.value)}
                  />
                </div>
                <div className="space-y-3">
                  <div className="text-sm text-[color:var(--muted)]">Chunking Strategy</div>
                  <select
                    className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                    value={settingsState.chunk_strategy_id}
                    onChange={(e) =>
                      setSettingsState({ ...settingsState, chunk_strategy_id: e.target.value })
                    }
                  >
                    <option value="">Default (active)</option>
                    {chunkStrategies.map((strategy) => (
                      <option key={strategy.id} value={strategy.id}>
                        {strategy.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              {settingsMessage && (
                <div className="text-sm text-[color:var(--muted)]">{settingsMessage}</div>
              )}
              <button
                className="px-6 py-2 rounded-xl bg-[color:var(--accent)] text-white"
                onClick={handleSaveSettings}
              >
                Save Settings
              </button>
            </section>
          )}

          {active === "Organization" && (
            <section className="card p-6 fade-in space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="font-display text-xl">Organization</h3>
                <span className="badge">
                  {orgInfo ? `${orgInfo.name} · ${orgInfo.role}` : "Loading..."}
                </span>
              </div>
              {orgMetrics && (
                <div className="grid md:grid-cols-4 gap-4">
                  <div className="p-4 rounded-xl bg-[color:var(--bg-secondary)]">
                    <div className="text-sm text-[color:var(--muted)]">Tenants</div>
                    <div className="text-2xl font-semibold">{orgMetrics.total_tenants}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-[color:var(--bg-secondary)]">
                    <div className="text-sm text-[color:var(--muted)]">Users</div>
                    <div className="text-2xl font-semibold">{orgMetrics.total_users}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-[color:var(--bg-secondary)]">
                    <div className="text-sm text-[color:var(--muted)]">Documents</div>
                    <div className="text-2xl font-semibold">{orgMetrics.total_documents}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-[color:var(--bg-secondary)]">
                    <div className="text-sm text-[color:var(--muted)]">Queries</div>
                    <div className="text-2xl font-semibold">{orgMetrics.total_queries}</div>
                  </div>
                </div>
              )}
              {orgMetrics && (
                <div className="space-y-3">
                  <div className="text-sm text-[color:var(--muted)]">Team activity</div>
                  <div className="grid md:grid-cols-2 gap-4">
                    {orgMetrics.by_tenant.map((item) => (
                      <div key={item.tenant_id} className="p-4 rounded-xl bg-[color:var(--bg-secondary)]">
                        <div className="font-semibold">{item.tenant_name}</div>
                        <div className="text-sm text-[color:var(--muted)]">
                          Docs: {item.documents} · Queries: {item.queries}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {!isOrgAdmin && (
                <div className="text-sm text-[color:var(--muted)]">
                  You do not have admin access to create tenants.
                </div>
              )}
              {isOrgAdmin && (
                <div className="space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <input
                      className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
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
                      className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                      placeholder="Tenant slug (auto)"
                      value={tenantSlugInput}
                      onChange={(e) => setTenantSlugInput(e.target.value)}
                    />
                  </div>
                  {tenantCreateMessage && (
                    <div className="text-sm text-[color:var(--muted)]">{tenantCreateMessage}</div>
                  )}
                  <button
                    className="px-6 py-2 rounded-xl bg-[color:var(--accent-strong)] text-white"
                    onClick={handleCreateTenant}
                    disabled={tenantCreating}
                  >
                    {tenantCreating ? "Creating..." : "Create Tenant"}
                  </button>
                </div>
              )}
              {isOrgAdmin && (
                <div className="space-y-4 pt-4 border-t border-[color:var(--border)]">
                  <h4 className="font-display text-lg">Create User</h4>
                  <div className="grid md:grid-cols-2 gap-4">
                    <input
                      className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                      placeholder="Full name"
                      value={newUserName}
                      onChange={(e) => setNewUserName(e.target.value)}
                    />
                    <input
                      className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                      placeholder="Email"
                      value={newUserEmail}
                      onChange={(e) => setNewUserEmail(e.target.value)}
                    />
                  </div>
                  <input
                    className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                    placeholder="Temporary password (optional)"
                    value={newUserTempPassword}
                    onChange={(e) => setNewUserTempPassword(e.target.value)}
                  />
                  {newUserResetLink && (
                    <div className="p-3 rounded-xl bg-[color:var(--bg-secondary)] text-sm break-all">
                      Reset link: {newUserResetLink}
                    </div>
                  )}
                  {newUserMessage && <div className="text-sm text-[color:var(--muted)]">{newUserMessage}</div>}
                  <button
                    className="px-6 py-2 rounded-xl bg-[color:var(--accent)] text-white"
                    onClick={handleCreateUser}
                  >
                    Create User
                  </button>
                </div>
              )}
              {isOrgAdmin && (
                <div className="space-y-4 pt-4 border-t border-[color:var(--border)]">
                  <h4 className="font-display text-lg">Assign User to Tenant</h4>
                  <div className="grid md:grid-cols-3 gap-4">
                    <select
                      className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
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
                      className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
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
                      className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
                      value={assignRole}
                      onChange={(e) => setAssignRole(e.target.value)}
                    >
                      <option value="member">Member</option>
                      <option value="admin">Admin</option>
                      <option value="owner">Owner</option>
                    </select>
                  </div>
                  {assignMessage && <div className="text-sm text-[color:var(--muted)]">{assignMessage}</div>}
                  <button
                    className="px-6 py-2 rounded-xl bg-[color:var(--accent-strong)] text-white"
                    onClick={handleAssignUser}
                    disabled={assigning}
                  >
                    {assigning ? "Assigning..." : "Assign User"}
                  </button>
                  {newUserLabel && (
                    <div className="text-xs text-[color:var(--muted)]">
                      Last created user: {newUserLabel}
                    </div>
                  )}
                </div>
              )}
              <div className="space-y-3">
                <div className="text-sm text-[color:var(--muted)]">Tenants</div>
                {tenants.length === 0 ? (
                  <div className="text-sm text-[color:var(--muted)]">No tenants available.</div>
                ) : (
                  <div className="grid md:grid-cols-2 gap-4">
                    {tenants.map((tenant) => (
                      <div key={tenant.id} className="p-4 rounded-xl bg-[color:var(--bg-secondary)] space-y-1">
                        <div className="font-semibold">{tenant.name}</div>
                        <div className="text-sm text-[color:var(--muted)]">{tenant.slug}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
