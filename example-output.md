# AWS re:Invent 2025 Keynote — December 2, 2025

## Summary
This keynote from AWS re:Invent 2025 in Las Vegas announced major updates across AWS's AI and infrastructure portfolio. With over 60,000 attendees in person and nearly 2 million watching online, the presentation unveiled the Nova 2 family of AI models, NovaForge for custom model training, comprehensive updates to Bedrock AgentCore platform, and significant compute instance expansions. Key themes included making AI agents production-ready, enabling developers to build faster with agentic tools like Kiro, and expanding infrastructure to support massive scale.

## Announcements

### Amazon Nova 2 Family (Nova 2 Light, Nova 2 Pro, Nova 2 Sonic, Nova 2 MM)
The Nova 2 family represents the next generation of Amazon's foundation models, including Nova 2 Light (fast, cost-effective reasoning for high-volume workloads), Nova 2 Pro (most intelligent reasoning model for complex workloads and agentic workflows), Nova 2 Sonic (speech-to-speech model for conversational AI), and Nova 2 MM (multimodal reasoning supporting text, image, video, and audio input with text and image generation output). All models support up to 1 million tokens of context.

- **Documentation**: https://docs.aws.amazon.com/nova/latest/nova2-userguide/what-is-nova-2.html
- **What's New / Blog**: https://aws.amazon.com/blogs/aws/top-announcements-of-aws-reinvent-2025/
- **Regional Availability**: Available through Amazon Bedrock in us-east-1, us-west-2, eu-west-1, and other Bedrock-supported regions
- **Getting Started**: https://docs.aws.amazon.com/nova/latest/nova2-userguide/getting-started-nova-2.html

### Amazon Bedrock AgentCore Platform
Comprehensive, modular platform for building, deploying, and operating AI agents securely at scale. Includes AgentCore Runtime (secure serverless environment), Memory (short and long-term context), Gateway (converts APIs to MCP-compatible tools), Identity (secure authentication and access management), Code Interpreter, Browser, Observability, Evaluations, and Policy. Works with any framework (CrewAI, LangGraph, LlamaIndex, Strands Agents) and any model.

- **Documentation**: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html
- **What's New / Blog**: https://aws.amazon.com/blogs/aws/introducing-amazon-bedrock-agentcore-securely-deploy-and-operate-ai-agents-at-any-scale/
- **Regional Availability**: Available in 9 AWS Regions including us-east-1, us-west-2, eu-west-1, ap-southeast-1
- **Getting Started**: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html

### Kiro (AI-Native Development Environment)
Agentic IDE that uses spec-driven development to transform development workflows. Features include turning prompts into detailed specs, autonomous agents that implement code, and hooks for automation. Now standardized internally across all of Amazon as the official AI development environment. Enables dramatically faster development cycles - one case study showed 6 developers completing an 18-month project in 76 days.

- **Documentation**: Use cases in AWS blogs including database and transformation guides
- **What's New / Blog**: https://aws.amazon.com/blogs/industries/from-spec-to-production-a-three-week-drug-discovery-agent-using-kiro/
- **Regional Availability**: Cloud-based IDE, accessible globally
- **Getting Started**: https://kiro.dev/ and AWS blog tutorials

### Amazon EC2 C8i Instances (Intel Xeon 6)
New compute-optimized instances powered by custom Intel Xeon 6 processors delivering up to 15% better price-performance and 2.5x more memory bandwidth compared to previous generation Intel-based instances. Available in C8i (13 sizes including 96xlarge) and C8i-flex variants (common sizes from large to 16xlarge).

- **Documentation**: https://aws.amazon.com/ec2/instance-types/c8i/
- **What's New / Blog**: https://aws.amazon.com/about-aws/whats-new/2025/09/amazon-ec2-c8i-and-c8i-flex-instances-generally-available/
- **Regional Availability**: US East (N. Virginia), US East (Ohio), US West (Oregon), Europe (Spain)
- **Getting Started**: Available via AWS Console, CLI, CloudFormation, SAM, and CDK

### Amazon EC2 M4 Max and M3 Ultra Mac Instances
New Mac instances powered by latest Apple silicon for building, testing, and signing Apple apps in the cloud. M4 Max features 16-core CPU, 40-core GPU, 16-core Neural Engine, and 128GB unified memory. Delivers up to 25% better application build performance compared to M1 Ultra Mac instances.

- **Documentation**: https://aws.amazon.com/ec2/instance-types/mac/
- **What's New / Blog**: https://aws.amazon.com/about-aws/whats-new/2026/01/amazon-ec2-m4-max-mac-instances-ga/
- **Regional Availability**: US East (N. Virginia), US West (Oregon)
- **Getting Started**: Available through EC2 Mac Dedicated Hosts

## ⭐ Flagged Moments

### ⭐ Amazon NovaForge (Open Training Models)
Service that introduces "open training models" - providing access to Nova training checkpoints across pre-training, mid-training, and post-training phases. Allows organizations to blend proprietary data with Amazon-curated training datasets to create custom "Novella" models that deeply understand domain-specific knowledge while preserving foundational capabilities. Includes reinforcement fine-tuning with custom reward functions and Responsible AI Toolkit.

**Why you flagged this**: "how does open training actually work? workshop potential"

- **Documentation**: https://docs.aws.amazon.com/nova/latest/nova2-userguide/nova-forge.html
- **What's New / Blog**: https://aws.amazon.com/blogs/aws/introducing-amazon-nova-forge-build-your-own-frontier-models-using-nova/
- **Regional Availability**: US East (N. Virginia) with plans to expand to additional regions
- **Getting Started**: Requires SageMaker HyperPod cluster setup and subscription via IAM role tagging
- **Related Services**: 
  - Amazon SageMaker HyperPod - https://aws.amazon.com/sagemaker/hyperpod/
  - Amazon Bedrock for model hosting - https://aws.amazon.com/bedrock/
- **Architectural Guidance**: https://docs.aws.amazon.com/nova/latest/nova2-userguide/nova-forge-cpt.html (Continued Pre-Training guide)
- **Tutorials**: https://docs.aws.amazon.com/nova/latest/nova2-userguide/nova-forge.html (Setup and configuration)

**Workshop Potential**: NovaForge is ideal for hands-on workshops demonstrating:
- How to blend proprietary datasets with Nova checkpoints at different training stages
- Implementing data mixing strategies to prevent catastrophic forgetting
- Using reinforcement learning with custom reward functions
- Training domain-specific models for manufacturing, healthcare, or financial services use cases

### ⭐ AWS Lambda Durable Functions
New capability enabling multi-step applications and AI workflows with automatic state management, execution suspension for up to one year, and built-in error recovery. Uses checkpoint and replay mechanism called "durable execution" with operations like "steps" (business logic with retries) and "waits" (suspend without compute charges). Ideal for long-running processes including human-in-the-loop workflows, order fulfillment, payment processing, and coordinating AI agent tasks.

**Why you flagged this**: "what does this mean for long-running agents?"

- **Documentation**: https://docs.aws.amazon.com/lambda/latest/dg/durable-functions.html
- **What's New / Blog**: https://aws.amazon.com/blogs/aws/build-multi-step-applications-and-ai-workflows-with-aws-lambda-durable-functions/
- **Regional Availability**: US East (Ohio) at launch, Lambda available in us-east-1, us-east-2, us-west-2 and other standard Lambda regions
- **Getting Started**: Available for Python 3.13/3.14 and Node.js 22/24 runtimes via AWS Console, CLI, SAM, CDK
- **Related Services**:
  - Amazon EventBridge for event routing - https://aws.amazon.com/eventbridge/
  - AWS Step Functions (alternative for complex orchestration) - https://aws.amazon.com/step-functions/
  - Amazon Bedrock AgentCore (pairs well for agent workflows) - https://aws.amazon.com/bedrock/
- **Architectural Guidance**: https://aws.amazon.com/blogs/compute/building-fault-tolerant-long-running-application-with-aws-lambda-durable-functions/
- **Tutorials**: 
  - https://docs.aws.amazon.com/lambda/latest/dg/workflow-event-management.html (Workflow management comparison)
  - Durable execution SDK documentation (open source on GitHub)

**Impact on Long-Running Agents**: Lambda Durable Functions transforms how autonomous agents operate by:
1. Enabling agents to pause execution during long waits (hours/days) without incurring compute charges
2. Automatically checkpointing agent state so interrupted workflows can resume exactly where they left off
3. Supporting human-in-the-loop patterns where agents wait for approvals or feedback
4. Handling multi-step agentic workflows (research → reasoning → action) with built-in retry logic
5. Providing serverless scaling for agent workloads without infrastructure management
6. Complementing AgentCore by handling the execution layer while AgentCore provides runtime, memory, and tooling

### Policy in Amazon Bedrock AgentCore
Natural language policy controls that convert to Cedar (AWS's open-source policy language) for deterministic enforcement of agent behavior. Policies sit outside agent code at the Gateway layer, intercepting all agent-tool interactions before execution. Enables fine-grained controls based on user identity and tool input parameters (e.g., "block refunds over $1000" or "only allow read access during business hours").

**Why you flagged this**: Part of the broader AgentCore announcement - enables production deployment of agents with compliance and security guarantees.

- **Documentation**: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html
- **What's New / Blog**: https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-in-amazon-bedrock-agentcore/
- **Regional Availability**: Generally available in 13 AWS Regions where AgentCore is available
- **Getting Started**: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-create-policies.html
- **Related Services**:
  - Cedar Policy Language - https://www.cedarpolicy.com/
  - Amazon CloudWatch (for policy enforcement logging) - https://aws.amazon.com/cloudwatch/
- **Architectural Guidance**: https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-in-amazon-bedrock-agentcore/ (Healthcare use case example)

## Reading List

### Priority (Flagged)

1. https://aws.amazon.com/blogs/aws/introducing-amazon-nova-forge-build-your-own-frontier-models-using-nova/ — NovaForge launch blog with detailed explanation of open training models and data mixing strategies
2. https://docs.aws.amazon.com/nova/latest/nova2-userguide/nova-forge-cpt.html — Technical guide for Continued Pre-Training with data mixing to prevent catastrophic forgetting
3. https://aws.amazon.com/blogs/aws/build-multi-step-applications-and-ai-workflows-with-aws-lambda-durable-functions/ — Lambda Durable Functions launch blog with order processing workflow example
4. https://docs.aws.amazon.com/lambda/latest/dg/durable-functions.html — Complete technical reference for Lambda durable functions including best practices
5. https://aws.amazon.com/blogs/compute/building-fault-tolerant-long-running-application-with-aws-lambda-durable-functions/ — Architectural patterns for fault-tolerant applications using durable functions
6. https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-in-amazon-bedrock-agentcore/ — Healthcare appointment scheduling agent demonstrating Policy in AgentCore

### All Announcements

1. https://docs.aws.amazon.com/nova/latest/nova2-userguide/what-is-nova-2.html — Nova 2 family overview and capabilities
2. https://aws.amazon.com/blogs/aws/top-announcements-of-aws-reinvent-2025/ — Complete summary of all re:Invent 2025 announcements
3. https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html — AgentCore platform architecture and services
4. https://aws.amazon.com/blogs/aws/introducing-amazon-bedrock-agentcore-securely-deploy-and-operate-ai-agents-at-any-scale/ — AgentCore launch blog with customer examples
5. https://aws.amazon.com/blogs/industries/from-spec-to-production-a-three-week-drug-discovery-agent-using-kiro/ — Kiro case study building production agent in 3 weeks
6. https://kiro.dev/ — Kiro official website and getting started
7. https://aws.amazon.com/ec2/instance-types/c8i/ — C8i instance specifications and use cases
8. https://aws.amazon.com/about-aws/whats-new/2026/01/amazon-ec2-m4-max-mac-instances-ga/ — M4 Max Mac instances announcement
9. https://aws.amazon.com/blogs/database/build-a-fitness-center-management-application-with-kiro-using-amazon-documentdb-with-mongodb-compatibility/ — Practical Kiro tutorial building complete application
10. https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-create-policies.html — Policy authoring guide with Cedar examples

---

**Infrastructure Scale Highlights Mentioned**:
- S3 now stores 500+ trillion objects (hundreds of exabytes)
- AWS added 3.8 gigawatts of data center capacity in 2025
- 9 million kilometers of terrestrial and subsea cable network (Earth to Moon and back 11 times)
- 38 regions, 120 availability zones globally
- Agent Core SDK downloaded 2+ million times in first few months

**Other Notable Announcements** (not detailed above):
- Kiro Autonomous Agent (frontier agent capability for long-running, massively scalable autonomous work)
- Amazon Oslot (quantum computing chip prototype reducing quantum error correction costs by 90%)
- C8g Graviton4 instances (mentioned briefly)
- Nova Multimodal Embeddings (launched weeks prior, state-of-the-art for semantic search)
- Graviton processors now power more than 50% of new CPU capacity added to AWS

**Developer Productivity Case Study**: Amazon internal team rearchitected a project estimated at 30 developers × 18 months, completed with 6 people in 76 days using agentic AI tools - demonstrating orders of magnitude efficiency improvement beyond typical 10-20% AI coding tool gains.
