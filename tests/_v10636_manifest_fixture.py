"""Test-only manifest metadata for the externalized Share Invite identity.

No workflow implementation is embedded in the Core repository; the real runtime
is shipped as the separately verified Share_Invite_v1.0.vpworkflow artifact.
"""
from vibrapilot.workflow import WorkflowManifest

SHARE_INVITE_MANIFEST = WorkflowManifest(
    workflow_id="share_invite",
    name="Share Invite",
    description="Authenticated Test Mode Share Invite workflow.",
    version="1.0",
    logo="assets/logo.png",
    entrypoint="create_workflow",
)
