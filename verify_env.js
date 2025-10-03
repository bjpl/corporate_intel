// Flow Nexus Environment Verification Script
// Run with: node verify_env.js

console.log('🔍 Flow Nexus Environment Check\n');

const requiredVars = {
  'ANTHROPIC_API_KEY': {
    description: 'Claude API access',
    pattern: /^sk-ant-api03-/,
    required: true
  },
  'E2B_API_KEY': {
    description: 'Sandbox environments',
    pattern: /^e2b_/,
    required: true
  },
  'GITHUB_TOKEN': {
    description: 'Repository analysis',
    pattern: /^gh[ps]_/,
    required: false
  }
};

let allGood = true;

Object.entries(requiredVars).forEach(([varName, config]) => {
  const value = process.env[varName];

  if (!value) {
    console.log(`❌ ${varName}: Missing`);
    console.log(`   Purpose: ${config.description}`);
    if (config.required) allGood = false;
  } else if (!config.pattern.test(value)) {
    console.log(`⚠️  ${varName}: Invalid format`);
    console.log(`   Expected pattern: ${config.pattern}`);
    if (config.required) allGood = false;
  } else {
    console.log(`✅ ${varName}: Configured`);
    console.log(`   Value: ${value.substring(0, 10)}...`);
  }
  console.log('');
});

console.log('📊 Flow Nexus Account Info:');
console.log(`   Email: brandon.lambert87@gmail.com`);
console.log(`   User ID: efc96d70-7a55-437b-b1f7-c903486da181`);
console.log(`   Credits: 667 rUv`);
console.log('');

if (allGood) {
  console.log('🎉 All required environment variables are set!');
  console.log('✨ Ready to use Flow Nexus!');
} else {
  console.log('🚨 Please set missing required environment variables.');
  console.log('💡 Restart your terminal/IDE after setting environment variables.');
}