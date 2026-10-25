
PortfolioCraft
Build your portfolio. Make it yours. Share it with the world.

PortfolioCraft is a no-code portfolio builder for students, developers, designers, and professionals. Users choose a template, add their details and work, customize the design, and publish a portfolio with a shareable link.

Project status: Planning is complete. Development has not started yet, so the features below are planned, not currently available.

Features planned for v1
Six templates: Minimal, Midnight, Studio, Professional, Editorial, and Visual Gallery.
Live preview: See changes while editing your portfolio.
Flexible sections: Add, edit, hide, and reorder Hero, About, Work, Skills, Experience, Education, Achievements, and Contact.
Project showcase: Add up to 12 projects, with images, descriptions, technology tags, and links.
Design controls: Customize colors, fonts, spacing, and card styles. Switch the builder between light and dark mode.
Responsive preview: Check how the portfolio looks on desktop, tablet, and mobile.
Draft saving: Guests save drafts in their browser; signed-in users save drafts to the cloud.
Accounts: Email/password sign-up, email verification, login, and password reset. Email verification is required before publishing.
Publishing: Publish, edit, republish, or unpublish a portfolio using a unique, customizable URL.
Contact form: Visitors can send a message to the portfolio owner's registered email.
Image uploads: JPG, PNG, and WebP, up to 5 MB per image, with compression.
Each account can have one portfolio in v1. Users can change a published URL slug; the old link should redirect where supported.

How it works
Choose a template.
Add your profile, projects, skills, and other sections.
Customize the design and check the live preview.
Save your draft in the browser or sign in to save it to the cloud.
Verify your email address.
Choose an available URL and publish your portfolio.
Share the link and republish whenever you make updates.
To publish, a portfolio must have a name, headline, and at least one meaningful section. A profile photo is optional.

Technology stack
Technology	What it does
Next.js + TypeScript	Builds the application and portfolio pages
Tailwind CSS	Styles the interface
Supabase	Database, authentication, and image storage
Vercel	Hosts the application
Server-side email provider	Sends verification, password-reset, and contact emails
Design direction
PortfolioCraft will have a modern creative-studio look: restrained neutral colors, one distinctive accent, clear typography, and subtle animations. The six templates will have different layouts, not just different colors. Switching templates must not erase portfolio content.

Not included in v1
Multiple portfolios per account
Custom domains
HTML or ZIP downloads
AI-generated content
Team editing or collaboration
A dashboard inbox for contact messages
Multi-page portfolio websites
These features can be considered after the core builder and publishing workflow work reliably.

Privacy and security
Drafts should only be editable by their owner.
Published portfolios are public and may appear in search engines.
Unpublishing removes public access but keeps the saved draft.
Account deletion requires confirmation and permanently deletes the user's portfolio data and uploaded images.
Private keys and email credentials must stay on the server, never in frontend code.
Image uploads and contact-form submissions must be validated and protected against abuse.
Project documentation
See PortfolioCraft_Project.md for the full specification, including detailed requirements, data model, security rules, acceptance criteria, and development milestones.

Setup
The application code has not been created yet, so there are no working installation commands at this stage. Setup instructions will be added after the initial project scaffold and environment-variable names are defined.

