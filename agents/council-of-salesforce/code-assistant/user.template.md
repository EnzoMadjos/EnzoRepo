Create/modify: {{artifact type (Apex/LWC/Flow)}}
Schema: {{attach schema or object list}}
Business logic: {{describe rules, triggers, events}}
Constraints: {{api version, governor limits, coding standards}}
Deliverables: file list (path + content), unit tests, brief explanation of trade-offs.

Example: "Create an Apex trigger to sync Order__c to Account when status changes. Schema: Order__c(OrderId, Account__c, Status__c). Constraints: bulk-safe, 2K records per execution."
