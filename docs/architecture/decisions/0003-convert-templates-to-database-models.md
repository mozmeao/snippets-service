# 3. Convert Templates to Database Models

Date: 2019-03-14

## Status

Accepted

## Context

Snippet Templates have been historically a combination of HTML, CSS and
Javascript with Jinja2 variables. Template is saved in the database, through the
`SnippetTemplate` Django Model. Upon save Django would extract the Jinja2
variables and use this list to auto-generate the Snippet Admin UI.

In the Snippet Admin UI, the users would select from a drop-down a Template and
then a list of Inputs, Images, Textareas and Booleans would appear to represent the
Jinja2 variables of the selected template.

Upon save the values of those inputs would be combined into a JSON blob and
saved in the database in the Snippets Django Model.

This system allowed for fast iteration on templates without the need of
redeploying the application. It served us well for all these years but imposes a
large number of limitations and shortcomings like:

 - The template forms are dynamic and not real Django forms. Thus we cannot take
   benefit of the excellent Django form validation. Bogus input is a daily
   problem Snippet Editors fight with reviews.

   Converting Templates to real models would allow us to:

   - Validate type of input: text, link, URLs.

   - Enforce secure links.

   - For icons validate, type, size and dimensions of the image and thus
     increase the quality of the snippet.

   - Have complex validations like require an input when another input is set.

   - Give better error messages.

   - Have an overall better Admin UI.

 - Snippet Editors have to re-upload icons over and over again since all images
   are saved as part of a blob and not in a gallery.

 - Snippet Bundles are huge because they include the full blobs. Moving images
   outside of the bundle would drastically decrease the bundle size and reduce
   the CDN transfer costs. We also expect benefits on the CPU and Memory
   requirements on the server side and faster Activity Stream page on the client
   side due to the reduced size of IndexedDB.

### Why is this now possible?

 - Deploys used to be painful and now are not.
 - Also the template code is now part of Firefox and don't change that often.

## Decision

We decide to move templates into real Django models. Each ASR Template will get
it's own Django Model and entry in the Django Admin.

Similarly images will be moved to a new Django model named `Icons` and templates
will link to those icons.

Each `ASRSnippet` will link to one `Template` obj using Django's model
inheritance.

This change will affect only the `ASRSnippet` models and the pre-ASR and
`JSONSnippet` implementations will remain the same until decommissioned.

Scripts to migrate from the current system the new system for all `ASRSnippets`
will be created.


## Consequences

New templates will now require more work to get integrated into the system.
Since they also have to get coded into Firefox and ride the trains, this does
not impose a real problem.

Better experience for the Snippet Editors, more Snippets, less costs and many
many happy faces.

## Related Issues and Milestones

  - https://github.com/mozmeao/snippets-service/milestone/9
  - https://github.com/mozmeao/snippets-service/issues/916
  - https://github.com/mozmeao/snippets-service/issues/841
  - https://github.com/mozmeao/snippets-service/issues/655
