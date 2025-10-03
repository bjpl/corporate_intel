// Flow Nexus Quick Start Helper
// Usage: node flow-nexus-quickstart.js [action]

const actions = {
  sandbox: {
    description: 'Create a development sandbox',
    example: `
// Create Node.js sandbox with Claude Code
mcp__flow-nexus__sandbox_create({
  template: "claude-code",
  name: "dev-sandbox",
  env_vars: {
    "ANTHROPIC_API_KEY": process.env.ANTHROPIC_API_KEY,
    "PROJECT_NAME": "corporate_intel"
  }
})
    `
  },

  swarm: {
    description: 'Initialize AI swarm for complex tasks',
    example: `
// Create mesh topology swarm
mcp__flow-nexus__swarm_init({
  topology: "mesh",
  maxAgents: 5,
  strategy: "adaptive"
})

// Spawn specialized agents
mcp__flow-nexus__agent_spawn({
  type: "coder",
  name: "backend-specialist"
})

mcp__flow-nexus__agent_spawn({
  type: "analyst",
  name: "data-processor"
})
    `
  },

  workflow: {
    description: 'Create automated workflow',
    example: `
// Create development workflow
mcp__flow-nexus__workflow_create({
  name: "corporate-intel-dev",
  description: "Development automation for corporate intel platform",
  steps: [
    {
      name: "code-analysis",
      agent_type: "analyst",
      task: "Analyze codebase structure"
    },
    {
      name: "feature-development",
      agent_type: "coder",
      task: "Implement new features"
    },
    {
      name: "testing",
      agent_type: "optimizer",
      task: "Run tests and optimize"
    }
  ]
})
    `
  },

  neural: {
    description: 'Set up neural network training',
    example: `
// Initialize neural cluster
mcp__flow-nexus__neural_cluster_init({
  name: "intel-processing",
  architecture: "transformer",
  daaEnabled: true,
  wasmOptimization: true
})
    `
  }
};

function showHelp() {
  console.log('🚀 Flow Nexus Quick Start Guide\n');
  console.log('Available actions:');

  Object.entries(actions).forEach(([action, config]) => {
    console.log(`\n📌 ${action.toUpperCase()}`);
    console.log(`   ${config.description}`);
    console.log(`   Usage: node flow-nexus-quickstart.js ${action}`);
  });

  console.log('\n💡 Use these examples in Claude Code with Flow Nexus MCP integration');
}

function showExample(action) {
  if (!actions[action]) {
    console.log(`❌ Unknown action: ${action}`);
    showHelp();
    return;
  }

  console.log(`🎯 ${action.toUpperCase()} Example:`);
  console.log(actions[action].example);
}

// Main execution
const action = process.argv[2];

if (!action) {
  showHelp();
} else {
  showExample(action);
}