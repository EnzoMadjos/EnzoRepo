# Lightning Web Components (LWC) — Salesforce Knowledge Base
> Source: LWC Developer Guide (API v67.0, Summer '26), trailheadapps/lwc-recipes
> Last updated: 2026-05-13

---

## 1. Component Structure

Every LWC has up to 4 files in a folder with the same name:
```
myComponent/
  myComponent.html          # Template (required)
  myComponent.js            # Controller (required)
  myComponent.css           # Styles (optional)
  myComponent.js-meta.xml   # Metadata config (required for deploy)
```

### Minimal Component
```html
<!-- myComponent.html -->
<template>
    <p>Hello, {name}!</p>
    <lightning-button label="Click me" onclick={handleClick}></lightning-button>
</template>
```
```js
// myComponent.js
import { LightningElement, track } from 'lwc';

export default class MyComponent extends LightningElement {
    name = 'World';          // reactive by default (no @track needed for primitives)

    handleClick() {
        this.name = 'Salesforce';
    }
}
```
```xml
<!-- myComponent.js-meta.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>67.0</apiVersion>
    <isExposed>true</isExposed>
    <targets>
        <target>lightning__RecordPage</target>
        <target>lightning__AppPage</target>
        <target>lightning__HomePage</target>
    </targets>
</LightningComponentBundle>
```

---

## 2. Reactive Properties

| Decorator | When to Use |
|---|---|
| (none) | Primitives (string, number, boolean) — auto-reactive |
| `@track` | Objects/arrays — deep changes trigger re-render |
| `@api` | Public property — expose to parent or Lightning App Builder |
| `@wire` | Wire an Apex method or data service |

```js
import { LightningElement, api, track, wire } from 'lwc';
import getAccount from '@salesforce/apex/AccountController.getAccount';

export default class AccountView extends LightningElement {
    @api recordId;                    // passed from record page
    @track accountData = {};          // deep reactive object

    @wire(getAccount, { accountId: '$recordId' })
    wiredAccount({ error, data }) {   // re-fires when recordId changes ($ prefix)
        if (data) {
            this.accountData = data;
        } else if (error) {
            console.error(error);
        }
    }
}
```

---

## 3. Lifecycle Hooks

| Hook | When Called | Use For |
|---|---|---|
| `constructor()` | When component created | Initialize vars — don't touch DOM |
| `connectedCallback()` | When component added to DOM | Subscribe to events, setup |
| `disconnectedCallback()` | When component removed | Unsubscribe, cleanup |
| `renderedCallback()` | After every render | 3rd party lib init (guard with flag) |
| `errorCallback(error, stack)` | When child throws | Error boundaries |

```js
import { LightningElement } from 'lwc';

export default class MyComponent extends LightningElement {
    isRendered = false;

    connectedCallback() {
        // Subscribe to message channel or event
    }

    renderedCallback() {
        if (this.isRendered) return;
        this.isRendered = true;
        // Initialize Chart.js or similar once
    }

    disconnectedCallback() {
        // Unsubscribe
    }
}
```

---

## 4. Component Communication

### Parent → Child (pass property)
```html
<!-- parent.html -->
<template>
    <c-child title={pageTitle} items={itemList}></c-child>
</template>
```
```js
// child.js
import { LightningElement, api } from 'lwc';
export default class Child extends LightningElement {
    @api title;
    @api items = [];
}
```

### Child → Parent (custom events)
```js
// child.js — fires event
import { LightningElement } from 'lwc';
export default class Child extends LightningElement {
    handleSave() {
        const event = new CustomEvent('save', { detail: { data: this.formData } });
        this.dispatchEvent(event);
    }
}
```
```html
<!-- parent.html — listens -->
<template>
    <c-child onsave={handleChildSave}></c-child>
</template>
```

### Cross-Component (Lightning Message Service)
```js
import { LightningElement, wire } from 'lwc';
import { MessageContext, publish, subscribe, unsubscribe } from 'lightning/messageService';
import MY_CHANNEL from '@salesforce/messageChannel/MyChannel__c';

export default class Publisher extends LightningElement {
    @wire(MessageContext) messageContext;

    sendMessage() {
        const payload = { recordId: this.recordId };
        publish(this.messageContext, MY_CHANNEL, payload);
    }
}

// Subscriber component
export default class Subscriber extends LightningElement {
    @wire(MessageContext) messageContext;
    subscription = null;

    connectedCallback() {
        this.subscription = subscribe(this.messageContext, MY_CHANNEL, (message) => {
            this.handleMessage(message);
        });
    }

    disconnectedCallback() {
        unsubscribe(this.subscription);
    }
}
```

---

## 5. Wire Service & Apex

### Apex Method Wiring
```js
// Apex: must be @AuraEnabled(cacheable=true) for wire
@AuraEnabled(cacheable=true)
public static List<Account> getAccounts(String industry) { ... }
```
```js
// LWC: wire with dynamic parameter ($ = reactive)
import { LightningElement, track, wire } from 'lwc';
import getAccounts from '@salesforce/apex/AccountController.getAccounts';

export default class AccountList extends LightningElement {
    @track industry = 'Technology';

    @wire(getAccounts, { industry: '$industry' })
    accounts;   // { data, error } object automatically set
}
```

### Imperative Apex Call (for non-cacheable / mutations)
```js
import saveAccount from '@salesforce/apex/AccountController.saveAccount';

export default class AccountForm extends LightningElement {
    handleSubmit() {
        saveAccount({ accountData: this.formData })
            .then(result => {
                this.dispatchEvent(new ShowToastEvent({
                    title: 'Success',
                    message: 'Account saved',
                    variant: 'success'
                }));
            })
            .catch(error => {
                console.error(error);
            });
    }
}
```

---

## 6. Lightning Data Service (LDS)

Use LDS for single-record CRUD — no Apex required, auto-cache management.

```html
<template>
    <lightning-record-view-form record-id={recordId} object-api-name="Account">
        <lightning-output-field field-name="Name"></lightning-output-field>
        <lightning-output-field field-name="Industry"></lightning-output-field>
    </lightning-record-view-form>
</template>
```

```html
<!-- Edit form -->
<template>
    <lightning-record-edit-form record-id={recordId} object-api-name="Account"
                                onsuccess={handleSuccess}>
        <lightning-input-field field-name="Name"></lightning-input-field>
        <lightning-input-field field-name="Rating"></lightning-input-field>
        <lightning-button type="submit" label="Save"></lightning-button>
    </lightning-record-edit-form>
</template>
```

### Wire: getRecord / getFieldValue
```js
import { wire } from 'lwc';
import { getRecord, getFieldValue } from 'lightning/uiRecordApi';
import ACCOUNT_NAME from '@salesforce/schema/Account.Name';

export default class AccountName extends LightningElement {
    @api recordId;

    @wire(getRecord, { recordId: '$recordId', fields: [ACCOUNT_NAME] })
    account;

    get name() {
        return getFieldValue(this.account.data, ACCOUNT_NAME);
    }
}
```

---

## 7. Slots (Content Projection)
```html
<!-- card.html (parent template) -->
<template>
    <div class="card">
        <slot name="header">Default Header</slot>
        <slot></slot>  <!-- default slot -->
    </div>
</template>
```
```html
<!-- usage -->
<template>
    <c-card>
        <span slot="header">My Title</span>
        <p>Card body content here</p>
    </c-card>
</template>
```

---

## 8. Performance Rules

| Rule | Why |
|---|---|
| Use `@wire` over imperative Apex for reads | Auto-caching, no extra network calls |
| Never call Apex in `renderedCallback` without guard | Fires every render — infinite loop |
| Use `lightning-datatable` for lists, not `template for:each` with deep nesting | Virtual rendering |
| Mark Apex cacheable=true when possible | Platform-level cache, reduces server hits |
| Split large components | Faster rendering, better reuse |
| Use `@track` only for objects/arrays | Reduces over-rendering |

---

## 9. Testing (Jest)
```js
import { createElement } from 'lwc';
import MyComponent from 'c/myComponent';

describe('c-my-component', () => {
    afterEach(() => {
        while (document.body.firstChild) {
            document.body.removeChild(document.body.firstChild);
        }
    });

    it('renders correctly', () => {
        const element = createElement('c-my-component', { is: MyComponent });
        element.name = 'Test';
        document.body.appendChild(element);

        const p = element.shadowRoot.querySelector('p');
        expect(p.textContent).toBe('Hello, Test!');
    });

    it('fires save event on button click', () => {
        const element = createElement('c-my-component', { is: MyComponent });
        document.body.appendChild(element);

        const handler = jest.fn();
        element.addEventListener('save', handler);

        const button = element.shadowRoot.querySelector('lightning-button');
        button.click();

        expect(handler).toHaveBeenCalled();
    });
});
```

---

## 10. Common Lightning Base Components
| Component | Use |
|---|---|
| `<lightning-card>` | Card container with header/footer slots |
| `<lightning-button>` | Styled button with icon support |
| `<lightning-input>` | Text, number, checkbox, date, toggle |
| `<lightning-combobox>` | Dropdown select |
| `<lightning-datatable>` | Sortable/filterable data table |
| `<lightning-record-edit-form>` | Auto-layout edit form for any object |
| `<lightning-record-view-form>` | Auto-layout view form |
| `<lightning-output-field>` | Read-only field in view form |
| `<lightning-input-field>` | Editable field in edit form |
| `<lightning-formatted-text>` | Rich text output |
| `<lightning-flow>` | Embed a Flow in a component |
| `<lightning-icon>` | SLDS icon |
| `<lightning-spinner>` | Loading spinner |
| `<lightning-toast>` | Toast notifications (ShowToastEvent) |

---

## Key Repos
| Repo | Purpose |
|---|---|
| [trailheadapps/lwc-recipes](https://github.com/trailheadapps/lwc-recipes) | 70+ component examples |
| [salesforce/lwc](https://github.com/salesforce/lwc) | LWC Open Source engine |
| [LWC Documentation](https://developer.salesforce.com/docs/component-library) | Component API reference |
