import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";
import AdminLayout from "../views/AdminLayout.vue";
import LoginPage from "../views/LoginPage.vue";
import AssessmentEntryPage from "../views/AssessmentEntryPage.vue";
import AssessmentFillPage from "../views/AssessmentFillPage.vue";
import AssessmentSuccessPage from "../views/AssessmentSuccessPage.vue";
import CandidatesPage from "../views/CandidatesPage.vue";
import JobProfilesPage from "../views/JobProfilesPage.vue";
import ProfessionalAssessment from "../views/ProfessionalAssessment.vue";
import QuestionnaireCenter from "../views/QuestionnaireCenter.vue";
import SettingsPage from "../views/SettingsPage.vue";
import UserManagementPage from "../views/UserManagementPage.vue";
import { useAuthStore } from "../stores/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    component: AdminLayout,
    children: [
      {
        path: "",
        redirect: "/candidates",
      },
      // 画像中心
      {
        path: "candidates",
        name: "candidates",
        component: CandidatesPage,
      },
      {
        path: "jobprofiles",
        name: "jobprofiles",
        component: JobProfilesPage,
      },
      {
        path: "assessments",
        name: "assessments",
        component: ProfessionalAssessment,
        meta: { category: "professional", title: "专业测评", icon: "ri-file-list-3-line" },
      },
      // 问卷中心 - 使用新组件
      {
        path: "questionnaire-center",
        name: "questionnaire-center",
        component: QuestionnaireCenter,
        meta: { category: "custom", title: "问卷中心", icon: "ri-questionnaire-line" },
      },
      // 人员管理
      {
        path: "users",
        name: "users",
        component: UserManagementPage,
      },
      // 系统设置
      {
        path: "settings",
        name: "settings",
        component: SettingsPage,
      },
    ],
  },
  {
    path: "/login",
    name: "login",
    component: LoginPage,
  },
  // 候选人端路由（公开访问，无需认证）
  {
    path: "/assessment/:code",
    name: "assessment-entry",
    component: AssessmentEntryPage,
    meta: { public: true },
  },
  {
    path: "/assessment/:code/fill/:submissionCode",
    name: "assessment-fill",
    component: AssessmentFillPage,
    meta: { public: true },
  },
  {
    path: "/assessment/:code/success/:submissionCode",
    name: "assessment-success",
    component: AssessmentSuccessPage,
    meta: { public: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  // 公开页面无需认证
  if (to.name === "login" || to.meta.public) return next();
  
  const auth = useAuthStore();
  const token = auth.token || localStorage.getItem("token");
  // ✅ 启用认证检查
  if (!token) return next({ name: "login" });
  next();
});

export default router;
