# Observer Mode 2.0 - Workflow Auto-Generation

Observer Mode 2.0 is a powerful feature that allows you to record browser sessions and automatically convert them into editable Skyvern workflows.

## Overview

Observer Mode captures:
- **User Interactions**: Clicks, inputs, navigation, and other browser actions
- **DOM Snapshots**: Complete page states at key moments
- **Reasoning Commentary**: Optional context about why each action was taken

These recordings are then analyzed by LLM to generate structured workflows with proper blocks and parameters.

## Architecture

### Backend Components

#### 1. Database Models (`skyvern/forge/sdk/db/models.py`)

Four new tables support Observer Mode:

- **`observer_sessions`**: Main session records
  - Tracks recording status, metadata, and generated workflows
  - Links to browser sessions and workflow permanent IDs

- **`observer_recordings`**: Individual recording entries
  - Stores sequence of actions with timestamps
  - Contains interaction data and reasoning

- **`observer_dom_snapshots`**: Page state captures
  - Full HTML content and screenshots
  - Linked to specific recordings

- **`observer_interactions`**: Detailed interaction tracking
  - Element selectors, XPaths, and interaction data
  - Timestamps for replay ordering

#### 2. Service Layer (`skyvern/services/observer_mode.py`)

Core service functions:

- `create_observer_session()` - Initialize a new recording session
- `record_interaction()` - Capture user interactions
- `capture_dom_snapshot()` - Save page state
- `generate_workflow_from_recording()` - LLM-powered conversion to workflow
- `complete_observer_session()` - Finalize recording
- `export_observer_session()` / `import_observer_session()` - Data portability
- `diff_recording_vs_workflow()` - Compare recorded steps with generated blocks

#### 3. API Routes (`skyvern/forge/sdk/routes/observer_mode.py`)

RESTful endpoints:

```
POST   /observer/sessions                      - Create session
GET    /observer/sessions                      - List sessions
GET    /observer/sessions/{session_id}         - Get session details
POST   /observer/sessions/{session_id}/interactions - Record interaction
POST   /observer/sessions/{session_id}/complete    - Complete session
POST   /observer/sessions/{session_id}/generate-workflow - Generate workflow
POST   /observer/sessions/{session_id}/export      - Export session data
POST   /observer/sessions/import                   - Import session data
POST   /observer/sessions/{session_id}/diff        - Compare recording vs workflow
DELETE /observer/sessions/{session_id}             - Delete session
```

#### 4. LLM Prompt (`skyvern/forge/prompts/skyvern/observer_mode_generate_workflow.j2`)

Template for instructing the LLM to:
- Analyze interaction sequences
- Identify logical groupings (navigation, tasks, extraction)
- Extract parameters from recorded values
- Generate proper workflow block structure

### Frontend Components

#### 1. Observer Sessions Page (`skyvern-frontend/src/routes/observer/ObserverSessionsPage.tsx`)

Main dashboard for observer sessions:
- List all recording sessions
- Create new sessions
- View session status (recording, completed, processing, failed)
- Navigate to session details

#### 2. Observer Session Detail (`skyvern-frontend/src/routes/observer/ObserverSessionDetail.tsx`)

Detailed session view with tabs:
- **Recordings**: Timeline of captured interactions
- **Generated Workflow**: Preview and edit workflow blocks
- **Diff View**: Side-by-side comparison of recordings and workflow

## Usage

### 1. Start Recording

```bash
curl -X POST https://api.skyvern.com/v1/observer/sessions \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Recording",
    "description": "Recording login flow",
    "start_url": "https://example.com",
    "browser_session_id": "optional_browser_session"
  }'
```

### 2. Record Interactions

As you interact with the browser, record each action:

```bash
curl -X POST https://api.skyvern.com/v1/observer/sessions/{session_id}/interactions \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "interaction_type": "click",
    "url": "https://example.com/login",
    "element_selector": "button#login-btn",
    "reasoning": "Click login button to proceed"
  }'
```

### 3. Complete Recording

```bash
curl -X POST https://api.skyvern.com/v1/observer/sessions/{session_id}/complete \
  -H "x-api-key: YOUR_API_KEY"
```

### 4. Generate Workflow

```bash
curl -X POST https://api.skyvern.com/v1/observer/sessions/{session_id}/generate-workflow \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Generated Login Workflow",
    "description": "Auto-generated from recording",
    "auto_publish": false
  }'
```

### 5. Review and Edit

The generated workflow will be created in draft status. You can:
- Review the workflow blocks
- Edit block parameters
- Add or remove steps
- Test the workflow
- Publish when ready

## Workflow Generation Logic

The LLM analyzes recordings to create workflows by:

1. **Grouping Actions**: Related interactions are combined into single blocks
2. **Identifying Patterns**: Repeated sequences become loop blocks
3. **Extracting Data**: Data collection steps become extraction blocks
4. **Parameterizing Values**: Dynamic values (URLs, inputs) become workflow parameters
5. **Adding Context**: Reasoning from recordings becomes block descriptions

### Example Transformation

**Recorded Interactions:**
```
1. Navigate to https://example.com
2. Click element: input#username
3. Input text: "testuser"
4. Click element: input#password
5. Input text: "password123"
6. Click element: button#submit
```

**Generated Workflow:**
```yaml
blocks:
  - label: navigate_to_login
    block_type: navigation
    url: "{{ base_url }}"
  
  - label: complete_login
    block_type: task
    url: "{{ base_url }}"
    navigation_goal: "Log in with provided credentials"
    data_extraction_goal: null

parameters:
  - key: base_url
    workflow_parameter_type: string
    description: "Base URL for the application"
    default_value: "https://example.com"
  
  - key: username
    workflow_parameter_type: string
    description: "Login username"
  
  - key: password
    workflow_parameter_type: string
    description: "Login password"
```

## Export/Import

### Export Session

```bash
curl -X POST https://api.skyvern.com/v1/observer/sessions/{session_id}/export \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"format": "json"}' \
  > session_export.json
```

### Import Session

```bash
curl -X POST https://api.skyvern.com/v1/observer/sessions/import \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @session_export.json
```

## Diff View

The diff feature helps you understand how recordings were translated:

```bash
curl -X POST https://api.skyvern.com/v1/observer/sessions/{session_id}/diff \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"workflow_id": "w_123"}' 
```

Returns:
```json
{
  "differences": [
    {
      "type": "matched",
      "recording_step": 1,
      "workflow_block": "navigate_to_login",
      "description": "Navigation recorded as navigation block"
    },
    {
      "type": "merged",
      "recording_step": "2-6",
      "workflow_block": "complete_login",
      "description": "Multiple interactions merged into task block"
    }
  ],
  "match_percentage": 95.0
}
```

## Best Practices

### Recording Tips

1. **Add Reasoning**: Include context about why you're taking each action
2. **Complete Workflows**: Record full end-to-end flows for best results
3. **Use Descriptive Titles**: Help identify sessions later
4. **Review Before Generating**: Ensure all critical interactions are captured

### Workflow Editing

1. **Review Parameters**: Check that extracted parameters make sense
2. **Test Thoroughly**: Run generated workflows with different inputs
3. **Refine Block Descriptions**: Improve generated descriptions for clarity
4. **Add Error Handling**: Consider edge cases not in the recording

### Performance

- Keep sessions focused on single workflows
- Don't record excessively long sessions
- Clean up old sessions periodically
- Use export/import for sharing reusable patterns

## Testing

Run the test suite:

```bash
pytest tests/unit_tests/services/test_observer_mode.py
```

Tests cover:
- Session creation and management
- Interaction recording
- Workflow generation logic
- Parameter extraction
- Export/import functionality
- Diff generation

## Future Enhancements

Potential improvements for Observer Mode:

1. **Browser Extension**: Chrome/Firefox extension for seamless recording
2. **Visual Recorder**: Interactive UI for recording with preview
3. **Smart Merging**: Automatically detect and merge similar recordings
4. **Template Library**: Save and share common workflow patterns
5. **A/B Testing**: Compare different workflow approaches
6. **Performance Metrics**: Track workflow efficiency vs manual steps

## Troubleshooting

### Common Issues

**Issue**: Workflow generation produces unexpected blocks
- **Solution**: Review recorded interactions for completeness; add more reasoning context

**Issue**: Parameters not extracted correctly
- **Solution**: Use consistent patterns in recorded values; manually edit after generation

**Issue**: Missing interactions in recording
- **Solution**: Ensure all browser events are captured; check for timing issues

**Issue**: Generated workflow fails to run
- **Solution**: Test with original recording conditions; adjust selectors if needed

## Support

For questions or issues:
- Check existing GitHub issues
- Review documentation at docs.skyvern.com
- Contact support@skyvern.com
