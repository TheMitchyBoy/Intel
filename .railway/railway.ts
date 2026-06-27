import {
  defineRailway,
  group,
  postgres,
  preserve,
  project,
  service,
} from "railway/iac";

export default defineRailway(() => {
  const Postgres = postgres("Postgres");

  const Throughline = service("Throughline", {
    healthcheck: "/health",
    healthcheckTimeout: 300,
    env: {
      DATABASE_URL: Postgres.env.DATABASE_URL,
      OPENAI_API_KEY: preserve(),
      API_KEY: preserve(),
    },
  });

  return project("Throughline", {
    resources: [group("Stack", [Postgres, Throughline])],
  });
});
