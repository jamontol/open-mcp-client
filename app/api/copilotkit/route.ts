import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
  LangChainAdapter
} from "@copilotkit/runtime";
import { LangGraphAgent } from "@copilotkit/runtime/langgraph"; // Add this import
import { NextRequest } from "next/server";
import { ChatOpenAI } from "@langchain/openai";

// You can use any service adapter here for multi-agent support.
const serviceAdapter = new LangChainAdapter({
  chainFn: async ({ messages, tools }) => {
    return model.bindTools(tools, { strict: true }).stream(messages);
  },
})

const langsmithApiKey = process.env.LANGSMITH_API_KEY as string;

const model = new ChatOpenAI({
  modelName: "gpt-4o-mini",
  temperature: 0,
  apiKey: process.env["OPENAI_API_KEY"],
});

const runtime = new CopilotRuntime({  
  // Use 'agents' instead of 'remoteEndpoints'
  agents: {
    sample_agent: new LangGraphAgent({
      deploymentUrl: process.env.AGENT_DEPLOYMENT_URL || "http://localhost:8123",
      langsmithApiKey,
      graphId: "orion_agent" //"sample_agent",
    }),
    }
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};