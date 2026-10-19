"""
BusinessHub message attachment storage.

Stores:
- Images as Cloudinary image resources.
- Audio and video as Cloudinary video resources.
- Other attachments as Cloudinary raw resources.

Preserves file extensions in stored names so Django can determine
the correct Cloudinary resource type when reopening attachments.
"""

import os

from django.core.files.uploadedfile import UploadedFile
from django.utils.deconstruct import deconstructible

from cloudinary_storage.storage import MediaCloudinaryStorage


@deconstructible
class MessageAttachmentCloudinaryStorage(MediaCloudinaryStorage):
    """Store message attachments using the appropriate resource type."""

    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
    }

    VIDEO_EXTENSIONS = {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".flv",
        ".3gp",
    }

    AUDIO_EXTENSIONS = {
        ".webm",
        ".ogg",
        ".mp3",
        ".wav",
        ".m4a",
    }

    MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

    def _get_resource_type(self, name):
        """
        Determine the Cloudinary resource type from the filename.
        """
        extension = os.path.splitext(name)[1].lower()

        if extension in self.IMAGE_EXTENSIONS:
            return "image"

        if (
            extension in self.AUDIO_EXTENSIONS
            or extension in self.VIDEO_EXTENSIONS
        ):
            return "video"

        return "raw"

    def _save(self, name, content):
        """
        Upload an attachment and preserve its extension in the
        filename stored by Django.

        Cloudinary may return a public ID without an extension for
        image and video uploads. Preserving the extension allows
        subsequent URL generation to identify the resource type.
        """
        name = self._normalise_name(name)
        name = self._prepend_prefix(name)

        extension = os.path.splitext(name)[1].lower()
        resource_type = self._get_resource_type(name)

        content = UploadedFile(content, name)
        response = self._upload(name, content)

        public_id = response["public_id"]

        if resource_type in {"image", "video"} and extension:
            if not public_id.lower().endswith(extension):
                public_id = f"{public_id}{extension}"

        return public_id

    def delete(self, name):
        """
        Delete an attachment using its actual Cloudinary public ID.

        Image and video extensions are removed because Cloudinary
        stores their format separately from the public ID.
        """
        resource_type = self._get_resource_type(name)
        public_id = name

        if resource_type in {"image", "video"}:
            extension = os.path.splitext(public_id)[1]

            if extension:
                public_id = public_id[:-len(extension)]

        response = self._destroy_resource(public_id, resource_type)

        return response.get("result") == "ok"

    @staticmethod
    def _destroy_resource(public_id, resource_type):
        """
        Delete a resource from Cloudinary.
        """
        import cloudinary

        return cloudinary.uploader.destroy(
            public_id,
            invalidate=True,
            resource_type=resource_type,
        )