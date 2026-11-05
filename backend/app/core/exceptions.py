from fastapi import HTTPException, status


class PayrollException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class ResourceNotFoundException(PayrollException):
    def __init__(self, resource: str, identifier: any):
        super().__init__(
            detail=f"{resource} with identifier '{identifier}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )


class DuplicateResourceException(PayrollException):
    def __init__(self, message: str):
        super().__init__(
            detail=message,
            status_code=status.HTTP_409_CONFLICT
        )


class PermissionDeniedException(PayrollException):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(
            detail=message,
            status_code=status.HTTP_403_FORBIDDEN
        )
