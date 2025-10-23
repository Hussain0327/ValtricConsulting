Skip to main content
DeepSeek API Docs Logo
DeepSeek API Docs
English
DeepSeek Platform

Quick Start
Your First API Call
Models & Pricing
The Temperature Parameter
Token & Token Usage
Rate Limit
Error Codes
News
DeepSeek-V3.2-Exp Release 2025/09/29
DeepSeek V3.1 Update 2025/09/22
DeepSeek V3.1 Release 2025/08/21
DeepSeek-R1-0528 Release 2025/05/28
DeepSeek-V3-0324 Release 2025/03/25
DeepSeek-R1 Release 2025/01/20
DeepSeek APP 2025/01/15
Introducing DeepSeek-V3 2024/12/26
DeepSeek-V2.5-1210 Release 2024/12/10
DeepSeek-R1-Lite Release 2024/11/20
DeepSeek-V2.5 Release 2024/09/05
Context Caching is Available 2024/08/02
New API Features 2024/07/25
API Reference
API Guides
V3.1-Terminus Comparison Testing
Reasoning Model (deepseek-reasoner)
Multi-round Conversation
Chat Prefix Completion (Beta)
FIM Completion (Beta)
JSON Output
Function Calling
Context Caching
Anthropic API
Other Resources
Integrations
API Status Page
FAQ
Change Log
NewsDeepSeek-V3.2-Exp Release 2025/09/29
Introducing DeepSeek-V3.2-Exp
🚀 Introducing DeepSeek-V3.2-Exp — our latest experimental model!

✨ Built on V3.1-Terminus, it debuts DeepSeek Sparse Attention (DSA) for faster, more efficient training & inference on long context.

👉 Now live on App, Web, and API

💰 API prices cut by 50%+!

⚡️ Efficiency Gains
🤖 DSA achieves fine-grained sparse attention with minimal impact on output quality — boosting long-context performance & reducing compute cost.

📊 Benchmarks show V3.2-Exp performs on par with V3.1-Terminus.



🧑‍💻 API Update
🎉 Lower costs, same access!

💰 DeepSeek API prices drop 50%+, effective immediately.

🔹 For comparison testing, V3.1-Terminus remains available via a temporary API until Oct 15th, 2025, 15:59 (UTC Time). Details: https://api-docs.deepseek.com/guides/comparison_testing

🔹 Feedback welcome: https://feedback.deepseek.com/dsa


🛠 Open Source Release
🔗 Model: https://huggingface.co/deepseek-ai/DeepSeek-V3.2-Exp

🔗 Tech report: https://github.com/deepseek-ai/DeepSeek-V3.2-Exp/blob/main/DeepSeek_V3_2.pdf

🔗 Key GPU kernels in TileLang & CUDA (use TileLang for rapid research prototyping!)

Previous
Error Codes
Next
DeepSeek-V3.1-Terminus
⚡️ Efficiency Gains
🧑‍💻 API Update
🛠 Open Source Release
WeChat Official Account
WeChat QRcode
Community
Email
Discord
Twitter
More
GitHub
Copyright © 2025 DeepSeek, Inc. 






/
Dashboard
Docs
API reference
Using GPT-5
Learn best practices, features, and migration guidance for GPT-5.
GPT-5 is our most intelligent model yet, trained to be especially proficient in:

Code generation, bug fixing, and refactoring
Instruction following
Long context and tool calling
This guide covers key features of the GPT-5 model family and how to get the most out of GPT-5.

Explore coding examples
Click through a few demo applications generated entirely with a single GPT-5 prompt, without writing any code by hand.

Quickstart
Faster responses
Coding and agentic tasks
By default, GPT-5 produces a medium length chain of thought before responding to a prompt. For faster, lower-latency responses, use low reasoning effort and low text verbosity.

This behavior will more closely (but not exactly!) match non-reasoning models like GPT-4.1. We expect GPT-5 to produce more intelligent responses than GPT-4.1, but when speed and maximum context length are paramount, you might consider using GPT-4.1 instead.
Fast, low latency response options
from openai import OpenAI
client = OpenAI()

result = client.responses.create(
    model="gpt-5",
    input="Write a haiku about code.",
    reasoning={ "effort": "low" },
    text={ "verbosity": "low" },
)

print(result.output_text)
Meet the models
There are three models in the GPT-5 series. In general, gpt-5 is best for your most complex tasks that require broad world knowledge. The smaller mini and nano models trade off some general world knowledge for lower cost and lower latency. Small models will tend to perform better for more well defined tasks.

To help you pick the model that best fits your use case, consider these tradeoffs:

Variant	Best for
gpt-5
Complex reasoning, broad world knowledge, and code-heavy or multi-step agentic tasks
gpt-5-mini
Cost-optimized reasoning and chat; balances speed, cost, and capability
gpt-5-nano
High-throughput tasks, especially simple instruction-following or classification
Model name reference
The GPT-5 system card uses different names than the API. Use this table to map between them:

System card name	API alias
gpt-5-thinking	gpt-5
gpt-5-thinking-mini	gpt-5-mini
gpt-5-thinking-nano	gpt-5-nano
gpt-5-main	gpt-5-chat-latest
gpt-5-main-mini	[not available via API]
New API features in GPT-5
Alongside GPT-5, we're introducing a few new parameters and API features designed to give developers more control and flexibility: the ability to control verbosity, a minimal reasoning effort option, custom tools, and an allowed tools list.

This guide walks through some of the key features of the GPT-5 model family and how to get the most out of these models.

Minimal reasoning effort
The reasoning.effort parameter controls how many reasoning tokens the model generates before producing a response. Earlier reasoning models like o3 supported only low, medium, and high: low favored speed and fewer tokens, while high favored more thorough reasoning.

The new minimal setting produces very few reasoning tokens for cases where you need the fastest possible time-to-first-token. We often see better performance when the model can produce a few tokens when needed versus none. The default is medium.

The minimal setting performs especially well in coding and instruction following scenarios, adhering closely to given directions. However, it may require prompting to act more proactively. To improve the model's reasoning quality, even at minimal effort, encourage it to “think” or outline its steps before answering.

Minimal reasoning effort
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-5",
    input="How much gold would it take to coat the Statue of Liberty in a 1mm layer?",
    reasoning={
        "effort": "minimal"
    }
)

print(response)
Verbosity
Verbosity determines how many output tokens are generated. Lowering the number of tokens reduces overall latency. While the model's reasoning approach stays mostly the same, the model finds ways to answer more concisely—which can either improve or diminish answer quality, depending on your use case. Here are some scenarios for both ends of the verbosity spectrum:

High verbosity: Use when you need the model to provide thorough explanations of documents or perform extensive code refactoring.
Low verbosity: Best for situations where you want concise answers or simple code generation, such as SQL queries.
Models before GPT-5 have used medium verbosity by default. With GPT-5, we make this option configurable as one of high, medium, or low.

When generating code, medium and high verbosity levels yield longer, more structured code with inline explanations, while low verbosity produces shorter, more concise code with minimal commentary.

Control verbosity
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-5",
    input="What is the answer to the ultimate question of life, the universe, and everything?",
    text={
        "verbosity": "low"
    }
)

print(response)
You can still steer verbosity through prompting after setting it to low in the API. The verbosity parameter defines a general token range at the system prompt level, but the actual output is flexible to both developer and user prompts within that range.

Custom tools
With GPT-5, we're introducing a new capability called custom tools, which lets models send any raw text as tool call input but still constrain outputs if desired.

Function calling guide
Learn about custom tools in the function calling guide.

Freeform inputs
Define your tool with type: custom to enable models to send plaintext inputs directly to your tools, rather than being limited to structured JSON. The model can send any raw text—code, SQL queries, shell commands, configuration files, or long-form prose—directly to your tool.

{
    "type": "custom",
    "name": "code_exec",
    "description": "Executes arbitrary python code",
}
Constraining outputs
GPT-5 supports context-free grammars (CFGs) for custom tools, letting you provide a Lark grammar to constrain outputs to a specific syntax or DSL. Attaching a CFG (e.g., a SQL or DSL grammar) ensures the assistant's text matches your grammar.

This enables precise, constrained tool calls or structured responses and lets you enforce strict syntactic or domain-specific formats directly in GPT-5's function calling, improving control and reliability for complex or constrained domains.

Best practices for custom tools
Write concise, explicit tool descriptions. The model chooses what to send based on your description; state clearly if you want it to always call the tool.
Validate outputs on the server side. Freeform strings are powerful but require safeguards against injection or unsafe commands.
Allowed tools
The allowed_tools parameter under tool_choice lets you pass N tool definitions but restrict the model to only M (< N) of them. List your full toolkit in tools, and then use an allowed_tools block to name the subset and specify a mode—either auto (the model may pick any of those) or required (the model must invoke one).

Function calling guide
Learn about the allowed tools option in the function calling guide.

By separating all possible tools from the subset that can be used now, you gain greater safety, predictability, and improved prompt caching. You also avoid brittle prompt engineering, such as hard-coded call order. GPT-5 dynamically invokes or requires specific functions mid-conversation while reducing the risk of unintended tool usage over long contexts.

Standard Tools	Allowed Tools
Model's universe	All tools listed under "tools": […]	Only the subset under "tools": […] in tool_choice
Tool invocation	Model may or may not call any tool	Model restricted to (or required to call) chosen tools
Purpose	Declare available capabilities	Constrain which capabilities are actually used
"tool_choice": {
    "type": "allowed_tools",
    "mode": "auto",
    "tools": [
      { "type": "function", "name": "get_weather" },
      { "type": "function", "name": "search_docs" }
    ]
  }
}'
For a more detailed overview of all of these new features, see the accompanying cookbook.

Preambles
Preambles are brief, user-visible explanations that GPT-5 generates before invoking any tool or function, outlining its intent or plan (e.g., “why I'm calling this tool”). They appear after the chain-of-thought and before the actual tool call, providing transparency into the model's reasoning and enhancing debuggability, user confidence, and fine-grained steerability.

By letting GPT-5 “think out loud” before each tool call, preambles boost tool-calling accuracy (and overall task success) without bloating reasoning overhead. To enable preambles, add a system or developer instruction—for example: “Before you call a tool, explain why you are calling it.” GPT-5 prepends a concise rationale to each specified tool call. The model may also output multiple messages between tool calls, which can enhance the interaction experience—particularly for minimal reasoning or latency-sensitive use cases.

For more on using preambles, see the GPT-5 prompting cookbook.

Migration guidance
GPT-5 is our best model yet, and it works best with the Responses API, which supports for passing chain of thought (CoT) between turns. Read below to migrate from your current model or API.

Migrating from other models to GPT-5
We see improved intelligence because the Responses API can pass the previous turn's CoT to the model. This leads to fewer generated reasoning tokens, higher cache hit rates, and less latency. To learn more, see an in-depth guide on the benefits of responses.

When migrating to GPT-5 from an older OpenAI model, start by experimenting with reasoning levels and prompting strategies. Based on our testing, we recommend using our prompt optimizer—which automatically updates your prompts for GPT-5 based on our best practices—and following this model-specific guidance:

o3: gpt-5 with medium or high reasoning is a great replacement. Start with medium reasoning with prompt tuning, then increasing to high if you aren't getting the results you want.
gpt-4.1: gpt-5 with minimal or low reasoning is a strong alternative. Start with minimal and tune your prompts; increase to low if you need better performance.
o4-mini or gpt-4.1-mini: gpt-5-mini with prompt tuning is a great replacement.
gpt-4.1-nano: gpt-5-nano with prompt tuning is a great replacement.
GPT-5 parameter compatibility
⚠️ Important: The following parameters are not supported when using GPT-5 models (e.g. gpt-5, gpt-5-mini, gpt-5-nano):

temperature
top_p
logprobs
Requests that include these fields will raise an error.

Instead, use the following GPT-5-specific controls:

Reasoning depth: reasoning: { effort: "minimal" | "low" | "medium" | "high" }
Output verbosity: text: { verbosity: "low" | "medium" | "high" }
Output length: max_output_tokens
Migrating from Chat Completions to Responses API
The biggest difference, and main reason to migrate from Chat Completions to the Responses API for GPT-5, is support for passing chain of thought (CoT) between turns. See a full comparison of the APIs.

Passing CoT exists only in the Responses API, and we've seen improved intelligence, fewer generated reasoning tokens, higher cache hit rates, and lower latency as a result of doing so. Most other parameters remain at parity, though the formatting is different. Here's how new parameters are handled differently between Chat Completions and the Responses API:

Reasoning effort

Responses API
Chat Completions
Generate response with minimal reasoning
curl --request POST \
--url https://api.openai.com/v1/responses \
--header "Authorization: Bearer $OPENAI_API_KEY" \
--header 'Content-type: application/json' \
--data '{
  "model": "gpt-5",
  "input": "How much gold would it take to coat the Statue of Liberty in a 1mm layer?",
  "reasoning": {
    "effort": "minimal"
  }
}'
Verbosity

Responses API
Chat Completions
Control verbosity
curl --request POST \
--url https://api.openai.com/v1/responses \
--header "Authorization: Bearer $OPENAI_API_KEY" \
--header 'Content-type: application/json' \
--data '{
  "model": "gpt-5",
  "input": "What is the answer to the ultimate question of life, the universe, and everything?",
  "text": {
    "verbosity": "low"
  }
}'
Custom tools

Responses API
Chat Completions
Custom tool call
curl --request POST --url https://api.openai.com/v1/responses --header "Authorization: Bearer $OPENAI_API_KEY" --header 'Content-type: application/json' --data '{
  "model": "gpt-5",
  "input": "Use the code_exec tool to calculate the area of a circle with radius equal to the number of r letters in blueberry",
  "tools": [
    {
      "type": "custom",
      "name": "code_exec",
      "description": "Executes arbitrary python code"
    }
  ]
}'
Prompting guidance
We specifically designed GPT-5 to excel at coding, frontend engineering, and tool-calling for agentic tasks. We also recommend iterating on prompts for GPT-5 using the prompt optimizer.

GPT-5 prompt optimizer
Craft the perfect prompt for GPT-5 in the dashboard

GPT-5 prompting guide
Learn full best practices for prompting GPT-5 models

Frontend prompting for GPT-5
See prompt samples specific to frontend development

GPT-5 is a reasoning model
Reasoning models like GPT-5 break problems down step by step, producing an internal chain of thought that encodes their reasoning. To maximize performance, pass these reasoning items back to the model: this avoids re-reasoning and keeps interactions closer to the model's training distribution. In multi-turn conversations, passing a previous_response_id automatically makes earlier reasoning items available. This is especially important when using tools—for example, when a function call requires an extra round trip. In these cases, either include them with previous_response_id or add them directly to input.

Learn more about reasoning models and how to get the most out of them in our reasoning guide.

Further reading
GPT-5 prompting guide

GPT-5 frontend guide

GPT-5 new features guide

Cookbook on reasoning models

Comparison of Responses API vs. Chat Completions

FAQ
How are these models integrated into ChatGPT?

In ChatGPT, there are two models: gpt-5-chat and gpt-5-thinking. They offer reasoning and minimal-reasoning capabilities, with a routing layer that selects the best model based on the user's question. Users can also invoke reasoning directly through the ChatGPT UI.

Will these models be supported in Codex?

Yes, gpt-5 will be available in Codex and Codex CLI.

How does GPT-5 compare to GPT-5-Codex?

GPT-5-Codex
 was specifically designed for use in Codex. Unlike GPT-5, which is a general-purpose model, we recommend using GPT-5-Codex only for agentic coding tasks in Codex or Codex-like environments, and GPT-5 for use cases in other domains. GPT-5-Codex is only available in the Responses API and supports low, medium, and high reasoning_efforts and function calling, structured outputs, and the web_search tool.

What is the deprecation plan for previous models?

Any model deprecations will be posted on our deprecations page. We'll send advanced notice of any model deprecations.

Was this page useful?
Overview
Quickstart
Meet the models
Minimal reasoning effort
Verbosity
Custom tools
Allowed tools
Preambles
Migration guidance
Prompting guidance
Further reading
FAQ
Prompting guide
GPT-5 best practices

/
Dashboard
Docs
API reference
Migrate to the Responses API
The Responses API is our new API primitive, an evolution of Chat Completions which brings added simplicity and powerful agentic primitives to your integrations.

While Chat Completions remains supported, Responses is recommended for all new projects.

About the Responses API
The Responses API is a unified interface for building powerful, agent-like applications. It contains:

Built-in tools like web search, file search , computer use, code interpreter, and remote MCPs.
Seamless multi-turn interactions that allow you to pass previous responses for higher accuracy reasoning results.
Native multimodal support for text and images.
Responses benefits
The Responses API contains several benefits over Chat Completions:

Better performance: Using reasoning models, like GPT-5, with Responses will result in better model intelligence when compared to Chat Completions. Our internal evals reveal a 3% improvement in SWE-bench with same prompt and setup.
Agentic by default: The Responses API is an agentic loop, allowing the model to call multiple tools, like web_search, image_generation, file_search, code_interpreter, remote MCP servers, as well as your own custom functions, within the span of one API request.
Lower costs: Results in lower costs due to improved cache utilization (40% to 80% improvement when compared to Chat Completions in internal tests).
Stateful context: Use store: true to maintain state from turn to turn, preserving reasoning and tool context from turn-to-turn.
Flexible inputs: Pass a string with input or a list of messages; use instructions for system-level guidance.
Encrypted reasoning: Opt-out of statefulness while still benefiting from advanced reasoning.
Future-proof: Future-proofed for upcoming models.
Capabilities	Chat Completions API	Responses API
Text generation		
Audio		Coming soon
Vision		
Structured Outputs		
Function calling		
Web search		
File search		
Computer use		
Code interpreter		
MCP		
Image generation		
Reasoning summaries		
Examples
See how the Responses API compares to the Chat Completions API in specific scenarios.

Messages vs. Items
Both APIs make it easy to generate output from our models. The input to, and result of, a call to Chat completions is an array of Messages, while the Responses API uses Items. An Item is a union of many types, representing the range of possibilities of model actions. A message is a type of Item, as is a function_call or function_call_output. Unlike a Chat Completions Message, where many concerns are glued together into one object, Items are distinct from one another and better represent the basic unit of model context.

Additionally, Chat Completions can return multiple parallel generations as choices, using the n param. In Responses, we've removed this param, leaving only one generation.

Chat Completions API
from openai import OpenAI
client = OpenAI()

completion = client.chat.completions.create(
  model="gpt-5",
  messages=[
      {
          "role": "user",
          "content": "Write a one-sentence bedtime story about a unicorn."
      }
  ]
)

print(completion.choices[0].message.content)
Responses API
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
  model="gpt-5",
  input="Write a one-sentence bedtime story about a unicorn."
)

print(response.output_text)
When you get a response back from the Responses API, the fields differ slightly. Instead of a message, you receive a typed response object with its own id. Responses are stored by default. Chat completions are stored by default for new accounts. To disable storage when using either API, set store: false.

The objects you recieve back from these APIs will differ slightly. In Chat Completions, you receive an array of choices, each containing a message. In Responses, you receive an array of Items labled output.

Chat Completions API
{
  "id": "chatcmpl-C9EDpkjH60VPPIB86j2zIhiR8kWiC",
  "object": "chat.completion",
  "created": 1756315657,
  "model": "gpt-5-2025-08-07",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Under a blanket of starlight, a sleepy unicorn tiptoed through moonlit meadows, gathering dreams like dew to tuck beneath its silver mane until morning.",
        "refusal": null,
        "annotations": []
      },
      "finish_reason": "stop"
    }
  ],
  ...
}
Responses API
{
  "id": "resp_68af4030592c81938ec0a5fbab4a3e9f05438e46b5f69a3b",
  "object": "response",
  "created_at": 1756315696,
  "model": "gpt-5-2025-08-07",
  "output": [
    {
      "id": "rs_68af4030baa48193b0b43b4c2a176a1a05438e46b5f69a3b",
      "type": "reasoning",
      "content": [],
      "summary": []
    },
    {
      "id": "msg_68af40337e58819392e935fb404414d005438e46b5f69a3b",
      "type": "message",
      "status": "completed",
      "content": [
        {
          "type": "output_text",
          "annotations": [],
          "logprobs": [],
          "text": "Under a quilt of moonlight, a drowsy unicorn wandered through quiet meadows, brushing blossoms with her glowing horn so they sighed soft lullabies that carried every dreamer gently to sleep."
        }
      ],
      "role": "assistant"
    }
  ],
  ...
}
Additional differences
Responses are stored by default. Chat completions are stored by default for new accounts. To disable storage in either API, set store: false.
Reasoning models have a richer experience in the Responses API with improved tool usage.
Structured Outputs API shape is different. Instead of response_format, use text.format in Responses. Learn more in the Structured Outputs guide.
The function-calling API shape is different, both for the function config on the request, and function calls sent back in the response. See the full difference in the function calling guide.
The Responses SDK has an output_text helper, which the Chat Completions SDK does not have.
In Chat Completions, conversation state must be managed manually. The Responses API has compatibility with the Conversations API for persistent conversations, or the ability to pass a previous_response_id to easily chain Responses together.
Migrating from Chat Completions
1. Update generation endpoints
Start by updating your generation endpoints from post /v1/chat/completions to post /v1/responses.

If you are not using functions or multimodal inputs, then you're done! Simple message inputs are compatible from one API to the other:

Web search tool
const context = [
  { role: 'system', content: 'You are a helpful assistant.' },
  { role: 'user', content: 'Hello!' }
];

const completion = await client.chat.completions.create({
  model: 'gpt-5',
  messages: messages
});

const response = await client.responses.create({
  model: "gpt-5",
  input: context
});
Chat Completions
Responses
With Chat Completions, you need to create an array of messages that specify different roles and content for each role.
Generate text from a model
import OpenAI from 'openai';
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const completion = await client.chat.completions.create({
  model: 'gpt-5',
  messages: [
    { 'role': 'system', 'content': 'You are a helpful assistant.' },
    { 'role': 'user', 'content': 'Hello!' }
  ]
});
console.log(completion.choices[0].message.content);
2. Update item definitions
Chat Completions
Responses
With Chat Completions, you need to create an array of messages that specify different roles and content for each role.
Generate text from a model
import OpenAI from 'openai';
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const completion = await client.chat.completions.create({
  model: 'gpt-5',
  messages: [
    { 'role': 'system', 'content': 'You are a helpful assistant.' },
    { 'role': 'user', 'content': 'Hello!' }
  ]
});
console.log(completion.choices[0].message.content);
3. Update multi-turn conversations
If you have multi-turn conversations in your application, update your context logic.

Chat Completions
Responses
In Chat Completions, you have to store and manage context yourself.
Multi-turn conversation
let messages = [
    { 'role': 'system', 'content': 'You are a helpful assistant.' },
    { 'role': 'user', 'content': 'What is the capital of France?' }
  ];
const res1 = await client.chat.completions.create({
  model: 'gpt-5',
  messages
});

messages = messages.concat([res1.choices[0].message]);
messages.push({ 'role': 'user', 'content': 'And its population?' });

const res2 = await client.chat.completions.create({
  model: 'gpt-5',
  messages
});
4. Decide when to use statefulness
Some organizations—such as those with Zero Data Retention (ZDR) requirements—cannot use the Responses API in a stateful way due to compliance or data retention policies. To support these cases, OpenAI offers encrypted reasoning items, allowing you to keep your workflow stateless while still benefiting from reasoning items.

To disable statefulness, but still take advantage of reasoning:

set store: false in the store field
add ["reasoning.encrypted_content"] to the include field
The API will then return an encrypted version of the reasoning tokens, which you can pass back in future requests just like regular reasoning items. For ZDR organizations, OpenAI enforces store=false automatically. When a request includes encrypted_content, it is decrypted in-memory (never written to disk), used for generating the next response, and then securely discarded. Any new reasoning tokens are immediately encrypted and returned to you, ensuring no intermediate state is ever persisted.

5. Update function definitions
There are two minor, but notable, differences in how functions are defined between Chat Completions and Responses.

In Chat Completions, functions are defined using externally tagged polymorphism, whereas in Responses, they are internally-tagged.
In Chat Completions, functions are non-strict by default, whereas in the Responses API, functions are strict by default.
The Responses API function example on the right is functionally equivalent to the Chat Completions example on the left.

Chat Completions API
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Determine weather in my location",
    "strict": true,
    "parameters": {
      "type": "object",
      "properties": {
        "location": {
          "type": "string",
        },
      },
      "additionalProperties": false,
      "required": [
        "location",
        "unit"
      ]
    }
  }
}
Responses API
{
  "type": "function",
  "name": "get_weather",
  "description": "Determine weather in my location",
  "parameters": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
      },
    },
    "additionalProperties": false,
    "required": [
      "location",
      "unit"
    ]
  }
}
Follow function-calling best practices
In Responses, tool calls and their outputs are two distinct types of Items that are correlated using a call_id. See the tool calling docs for more detail on how function calling works in Responses.

6. Update Structured Outputs definition
In the Responses API, defining structured outputs have moved from response_format to text.format:

Chat Completions
Responses
Structured Outputs
const completion = await openai.chat.completions.create({
  model: "gpt-5",
  messages: [
    {
      "role": "user",
      "content": "Jane, 54 years old",
    }
  ],
  response_format: {
    type: "json_schema",
    json_schema: {
      name: "person",
      strict: true,
      schema: {
        type: "object",
        properties: {
          name: {
            type: "string",
            minLength: 1
          },
          age: {
            type: "number",
            minimum: 0,
            maximum: 130
          }
        },
        required: [
          name,
          age
        ],
        additionalProperties: false
      }
    }
  },
  verbosity: "medium",
  reasoning_effort: "medium"
});
7. Upgrade to native tools
If your application has use cases that would benefit from OpenAI's native tools, you can update your tool calls to use OpenAI's tools out of the box.

Chat Completions
Responses
With Chat Completions, you cannot use OpenAI's tools natively and have to write your own.
Web search tool
async function web_search(query) {
    const fetch = (await import('node-fetch')).default;
    const res = await fetch(`https://api.example.com/search?q=${query}`);
    const data = await res.json();
    return data.results;
}

const completion = await client.chat.completions.create({
  model: 'gpt-5',
  messages: [
    { role: 'system', content: 'You are a helpful assistant.' },
    { role: 'user', content: 'Who is the current president of France?' }
  ],
  functions: [
    {
      name: 'web_search',
      description: 'Search the web for information',
      parameters: {
        type: 'object',
        properties: { query: { type: 'string' } },
        required: ['query']
      }
    }
  ]
});
Incremental migration
The Responses API is a superset of the Chat Completions API. The Chat Completions API will also continue to be supported. As such, you can incrementally adopt the Responses API if desired. You can migrate user flows who would benefit from improved reasoning models to the Responses API while keeping other flows on the Chat Completions API until you're ready for a full migration.

As a best practice, we encourage all users to migrate to the Responses API to take advantage of the latest features and improvements from OpenAI.

Assistants API
Based on developer feedback from the Assistants API beta, we've incorporated key improvements into the Responses API to make it more flexible, faster, and easier to use. The Responses API represents the future direction for building agents on OpenAI.

We now have Assistant-like and Thread-like objects in the Responses API. Learn more in the migration guide. As of August 26th, 2025, we're deprecating the Assistants API, with a sunset date of August 26, 2026.

Was this page useful?
About the Responses API
Responses benefits
Comparison to Chat Completions
Migrating from Chat Completions
Incremental migration

/
Dashboard
Docs
API reference
Reasoning models
Explore advanced reasoning and problem-solving models.
Reasoning models like GPT-5 are LLMs trained with reinforcement learning to perform reasoning. Reasoning models think before they answer, producing a long internal chain of thought before responding to the user. Reasoning models excel in complex problem solving, coding, scientific reasoning, and multi-step planning for agentic workflows. They're also the best models for Codex CLI, our lightweight coding agent.

We provide smaller, faster models (gpt-5-mini and gpt-5-nano) that are less expensive per token. The larger model (gpt-5) is slower and more expensive but often generates better responses for complex tasks and broad domains.

Reasoning models work better with the Responses API. While the Chat Completions API is still supported, you'll get improved model intelligence and performance by using Responses.

Get started with reasoning
Call the Responses API and specify your reasoning model and reasoning effort:

Using a reasoning model in the Responses API
from openai import OpenAI

client = OpenAI()

prompt = """
Write a bash script that takes a matrix represented as a string with 
format '[1,2],[3,4],[5,6]' and prints the transpose in the same format.
"""

response = client.responses.create(
    model="gpt-5",
    reasoning={"effort": "medium"},
    input=[
        {
            "role": "user", 
            "content": prompt
        }
    ]
)

print(response.output_text)
In the example above, the reasoning.effort parameter guides the model on how many reasoning tokens to generate before creating a response to the prompt.

Specify low, medium, or high for this parameter, where low favors speed and economical token usage, and high favors more complete reasoning. The default value is medium, which is a balance between speed and reasoning accuracy.

How reasoning works
Reasoning models introduce reasoning tokens in addition to input and output tokens. The models use these reasoning tokens to "think," breaking down the prompt and considering multiple approaches to generating a response. After generating reasoning tokens, the model produces an answer as visible completion tokens and discards the reasoning tokens from its context.

Here is an example of a multi-step conversation between a user and an assistant. Input and output tokens from each step are carried over, while reasoning tokens are discarded.

Reasoning tokens aren't retained in context

While reasoning tokens are not visible via the API, they still occupy space in the model's context window and are billed as output tokens.

Managing the context window
It's important to ensure there's enough space in the context window for reasoning tokens when creating responses. Depending on the problem's complexity, the models may generate anywhere from a few hundred to tens of thousands of reasoning tokens. The exact number of reasoning tokens used is visible in the usage object of the response object, under output_tokens_details:

{
    "usage": {
        "input_tokens": 75,
        "input_tokens_details": {
            "cached_tokens": 0
        },
        "output_tokens": 1186,
        "output_tokens_details": {
            "reasoning_tokens": 1024
        },
        "total_tokens": 1261
    }
}
Context window lengths are found on the model reference page, and will differ across model snapshots.

Controlling costs
To manage costs with reasoning models, you can limit the total number of tokens the model generates (including both reasoning and final output tokens) by using the 
max_output_tokens
 parameter.

Allocating space for reasoning
If the generated tokens reach the context window limit or the max_output_tokens value you've set, you'll receive a response with a status of incomplete and incomplete_details with reason set to max_output_tokens. This might occur before any visible output tokens are produced, meaning you could incur costs for input and reasoning tokens without receiving a visible response.

To prevent this, ensure there's sufficient space in the context window or adjust the max_output_tokens value to a higher number. OpenAI recommends reserving at least 25,000 tokens for reasoning and outputs when you start experimenting with these models. As you become familiar with the number of reasoning tokens your prompts require, you can adjust this buffer accordingly.

Handling incomplete responses
from openai import OpenAI

client = OpenAI()

prompt = """
Write a bash script that takes a matrix represented as a string with 
format '[1,2],[3,4],[5,6]' and prints the transpose in the same format.
"""

response = client.responses.create(
    model="gpt-5",
    reasoning={"effort": "medium"},
    input=[
        {
            "role": "user", 
            "content": prompt
        }
    ],
    max_output_tokens=300,
)

if response.status == "incomplete" and response.incomplete_details.reason == "max_output_tokens":
    print("Ran out of tokens")
    if response.output_text:
        print("Partial output:", response.output_text)
    else: 
        print("Ran out of tokens during reasoning")
Keeping reasoning items in context
When doing function calling with a reasoning model in the Responses API, we highly recommend you pass back any reasoning items returned with the last function call (in addition to the output of your function). If the model calls multiple functions consecutively, you should pass back all reasoning items, function call items, and function call output items, since the last user message. This allows the model to continue its reasoning process to produce better results in the most token-efficient manner.

The simplest way to do this is to pass in all reasoning items from a previous response into the next one. Our systems will smartly ignore any reasoning items that aren't relevant to your functions, and only retain those in context that are relevant. You can pass reasoning items from previous responses either using the previous_response_id parameter, or by manually passing in all the output items from a past response into the input of a new one.

For advanced use cases where you might be truncating and optimizing parts of the context window before passing them on to the next response, just ensure all items between the last user message and your function call output are passed into the next response untouched. This will ensure that the model has all the context it needs.

Check out this guide to learn more about manual context management.

Encrypted reasoning items
When using the Responses API in a stateless mode (either with store set to false, or when an organization is enrolled in zero data retention), you must still retain reasoning items across conversation turns using the techniques described above. But in order to have reasoning items that can be sent with subsequent API requests, each of your API requests must have reasoning.encrypted_content in the include parameter of API requests, like so:

curl https://api.openai.com/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "o4-mini",
    "reasoning": {"effort": "medium"},
    "input": "What is the weather like today?",
    "tools": [ ... function config here ... ],
    "include": [ "reasoning.encrypted_content" ]
  }'
Any reasoning items in the output array will now have an encrypted_content property, which will contain encrypted reasoning tokens that can be passed along with future conversation turns.

Reasoning summaries
While we don't expose the raw reasoning tokens emitted by the model, you can view a summary of the model's reasoning using the the summary parameter. See our model documentation to check which reasoning models support summaries.

Different models support different reasoning summary settings. For example, our computer use model supports the concise summarizer, while o4-mini supports detailed. To access the most detailed summarizer available for a model, set the value of this parameter to auto. auto will be equivalent to detailed for most reasoning models today, but there may be more granular settings in the future.

Reasoning summary output is part of the summary array in the reasoning output item. This output will not be included unless you explicitly opt in to including reasoning summaries.

The example below shows how to make an API request that includes a reasoning summary.

Include a reasoning summary with the API response
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-5",
    input="What is the capital of France?",
    reasoning={
        "effort": "low",
        "summary": "auto"
    }
)

print(response.output)
This API request will return an output array with both an assistant message and a summary of the model's reasoning in generating that response.

[
    {
        "id": "rs_6876cf02e0bc8192b74af0fb64b715ff06fa2fcced15a5ac",
        "type": "reasoning",
        "summary": [
            {
                "type": "summary_text",
                "text": "**Answering a simple question**\n\nI\u2019m looking at a straightforward question: the capital of France is Paris. It\u2019s a well-known fact, and I want to keep it brief and to the point. Paris is known for its history, art, and culture, so it might be nice to add just a hint of that charm. But mostly, I\u2019ll aim to focus on delivering a clear and direct answer, ensuring the user gets what they\u2019re looking for without any extra fluff."
            }
        ]
    },
    {
        "id": "msg_6876cf054f58819284ecc1058131305506fa2fcced15a5ac",
        "type": "message",
        "status": "completed",
        "content": [
            {
                "type": "output_text",
                "annotations": [],
                "logprobs": [],
                "text": "The capital of France is Paris."
            }
        ],
        "role": "assistant"
    }
]
Before using summarizers with our latest reasoning models, you may need to complete organization verification to ensure safe deployment. Get started with verification on the platform settings page.

Advice on prompting
There are some differences to consider when prompting a reasoning model. Reasoning models provide better results on tasks with only high-level guidance, while GPT models often benefit from very precise instructions.

A reasoning model is like a senior co-worker—you can give them a goal to achieve and trust them to work out the details.
A GPT model is like a junior coworker—they'll perform best with explicit instructions to create a specific output.
For more information on best practices when using reasoning models, refer to this guide.

Prompt examples
Coding (refactoring)
Coding (planning)
STEM Research
OpenAI o-series models are able to implement complex algorithms and produce code. This prompt asks o1 to refactor a React component based on some specific criteria.

Refactor code
import OpenAI from "openai";

const openai = new OpenAI();

const prompt = `
Instructions:
- Given the React component below, change it so that nonfiction books have red
  text. 
- Return only the code in your reply
- Do not include any additional formatting, such as markdown code blocks
- For formatting, use four space tabs, and do not allow any lines of code to 
  exceed 80 columns

const books = [
  { title: 'Dune', category: 'fiction', id: 1 },
  { title: 'Frankenstein', category: 'fiction', id: 2 },
  { title: 'Moneyball', category: 'nonfiction', id: 3 },
];

export default function BookList() {
  const listItems = books.map(book =>
    <li>
      {book.title}
    </li>
  );

  return (
    <ul>{listItems}</ul>
  );
}
`.trim();

const response = await openai.responses.create({
    model: "gpt-5",
    input: [
        {
            role: "user",
            content: prompt,
        },
    ],
});

console.log(response.output_text);
Use case examples
Some examples of using reasoning models for real-world use cases can be found in the cookbook.

Using reasoning for data validation
Evaluate a synthetic medical data set for discrepancies.

Using reasoning for routine generation
Use help center articles to generate actions that an agent could perform.

Was this page useful?
Get started
How reasoning works
Reasoning summaries
Advice on prompting
Use case examples