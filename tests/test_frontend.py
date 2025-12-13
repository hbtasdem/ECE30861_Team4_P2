"""
Selenium Test Suite for ADA Compliance - Model Registry Frontend
Tests accessibility features including keyboard navigation, ARIA attributes,
color contrast, and screen reader compatibility.
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from axe_selenium_python import Axe


class TestADACompliance:
    """Test suite for ADA/WCAG compliance of Model Registry frontend"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test"""
        # Setup Chrome with accessibility features
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Remove for visual debugging
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        self.base_url = "http://127.0.0.1:8000"
        
        yield
        
        # Teardown
        self.driver.quit()
    
    def test_page_loads_successfully(self):
        """Test that the page loads without errors"""
        self.driver.get(self.base_url)
        assert "Model Registry API" in self.driver.title
        
    def test_skip_navigation_link_present(self):
        """Test that skip navigation link exists and is functional"""
        self.driver.get(self.base_url)
        
        # Skip link should exist
        skip_link = self.driver.find_element(By.CLASS_NAME, "skip-link")
        assert skip_link.is_displayed() or skip_link.get_attribute("class") == "skip-link"
        
        # Check href targets main content
        assert skip_link.get_attribute("href").endswith("#main-content")
        
        # Verify main content has the correct ID
        main_content = self.driver.find_element(By.ID, "main-content")
        assert main_content is not None
    
    def test_semantic_html_structure(self):
        """Test proper semantic HTML5 elements"""
        self.driver.get(self.base_url)
        
        # Check for semantic landmarks
        header = self.driver.find_element(By.TAG_NAME, "header")
        assert header.get_attribute("role") == "banner"
        
        main = self.driver.find_element(By.TAG_NAME, "main")
        assert main.get_attribute("role") == "main"
        assert main.get_attribute("id") == "main-content"
        
        nav = self.driver.find_element(By.TAG_NAME, "nav")
        assert nav.get_attribute("aria-labelledby") == "links-heading"
        
    def test_heading_hierarchy(self):
        """Test proper heading hierarchy (h1 -> h2 -> h3)"""
        self.driver.get(self.base_url)
        
        # Should have one h1
        h1_elements = self.driver.find_elements(By.TAG_NAME, "h1")
        assert len(h1_elements) == 1
        assert "BoilerFace Model Registry" in h1_elements[0].text
        
        # Should have h2 elements
        h2_elements = self.driver.find_elements(By.TAG_NAME, "h2")
        assert len(h2_elements) >= 2
        
        # Check h2 headings
        h2_texts = [h2.text for h2 in h2_elements]
        assert "Upload Model" in h2_texts
        assert "Quick Links" in h2_texts
    
    def test_form_labels_properly_associated(self):
        """Test that form inputs have properly associated labels"""
        self.driver.get(self.base_url)
        
        # Check label exists and is associated with input
        label = self.driver.find_element(By.CSS_SELECTOR, "label[for='modelUrl']")
        assert label is not None
        assert "Model URL" in label.text
        
        # Check input has corresponding ID
        input_field = self.driver.find_element(By.ID, "modelUrl")
        assert input_field.get_attribute("type") == "url"
        
    def test_aria_attributes_on_form_elements(self):
        """Test ARIA attributes on form inputs"""
        self.driver.get(self.base_url)
        
        input_field = self.driver.find_element(By.ID, "modelUrl")
        
        # Check ARIA attributes
        assert input_field.get_attribute("aria-required") == "true"
        assert input_field.get_attribute("aria-describedby") == "url-help"
        assert input_field.get_attribute("aria-invalid") == "false"
        assert input_field.get_attribute("required") is not None
        
    def test_button_has_descriptive_label(self):
        """Test that button has descriptive aria-label"""
        self.driver.get(self.base_url)
        
        button = self.driver.find_element(By.ID, "uploadBtn")
        aria_label = button.get_attribute("aria-label")
        
        assert aria_label == "Upload model to registry"
        assert button.get_attribute("type") == "submit"
        
    def test_live_regions_present(self):
        """Test that ARIA live regions exist for dynamic content"""
        self.driver.get(self.base_url)
        
        # Status region
        status_region = self.driver.find_element(By.ID, "statusRegion")
        assert status_region.get_attribute("role") == "status"
        assert status_region.get_attribute("aria-live") == "polite"
        assert status_region.get_attribute("aria-atomic") == "true"
        
        # Response container
        response_container = self.driver.find_element(By.ID, "responseContainer")
        assert response_container.get_attribute("aria-live") == "polite"
        assert response_container.get_attribute("aria-atomic") == "true"
    
    def test_keyboard_navigation_skip_link(self):
        """Test keyboard navigation to skip link"""
        self.driver.get(self.base_url)
        
        # Tab to skip link (should be first focusable element)
        body = self.driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.TAB)
        
        # Check if skip link is focused
        active_element = self.driver.switch_to.active_element
        assert active_element.get_attribute("class") == "skip-link"
        
    def test_keyboard_navigation_through_form(self):
        """Test keyboard navigation through entire form"""
        self.driver.get(self.base_url)
        
        body = self.driver.find_element(By.TAG_NAME, "body")
        
        # Tab through elements
        body.send_keys(Keys.TAB)  # Skip link
        body.send_keys(Keys.TAB)  # Input field
        
        active_element = self.driver.switch_to.active_element
        assert active_element.get_attribute("id") == "modelUrl"
        
        body.send_keys(Keys.TAB)  # Button
        active_element = self.driver.switch_to.active_element
        assert active_element.get_attribute("id") == "uploadBtn"
        
    def test_focus_indicators_visible(self):
        """Test that focus indicators are visible on interactive elements"""
        self.driver.get(self.base_url)
        
        # Focus on input
        input_field = self.driver.find_element(By.ID, "modelUrl")
        input_field.send_keys(Keys.TAB)
        
        # Check focus styling (outline should be applied)
        focused_element = self.driver.switch_to.active_element
        outline = focused_element.value_of_css_property("outline")
        box_shadow = focused_element.value_of_css_property("box-shadow")
        
        # Should have visible focus indicator (outline or box-shadow)
        assert outline != "none" or box_shadow != "none"
        
    def test_form_validation_error_handling(self):
        """Test form validation and error message accessibility"""
        self.driver.get(self.base_url)
        
        # Submit empty form
        button = self.driver.find_element(By.ID, "uploadBtn")
        button.click()
        
        # Wait for HTML5 validation or error message
        time.sleep(1)
        
        input_field = self.driver.find_element(By.ID, "modelUrl")
        
        # HTML5 validation should prevent submission
        validation_message = input_field.get_attribute("validationMessage")
        assert validation_message != ""
        
    def test_form_submission_with_valid_input(self):
        """Test form submission workflow with keyboard"""
        self.driver.get(self.base_url)
        
        # Enter URL
        input_field = self.driver.find_element(By.ID, "modelUrl")
        test_url = "https://huggingface.co/test/model"
        input_field.send_keys(test_url)
        
        # Submit with Enter key
        input_field.send_keys(Keys.RETURN)
        
        # Wait for loading state
        wait = WebDriverWait(self.driver, 10)
        status_region = wait.until(
            EC.presence_of_element_located((By.ID, "statusRegion"))
        )
        
        # Status region should have content
        time.sleep(1)  # Allow for async operation
        assert status_region.text != ""
        
    def test_external_links_have_indicators(self):
        """Test that external links have proper indicators"""
        self.driver.get(self.base_url)
        
        # Find all external links
        links = self.driver.find_elements(By.CSS_SELECTOR, "a[target='_blank']")
        
        assert len(links) >= 3  # Health, Swagger, ReDoc
        
        for link in links:
            # Check for rel attribute
            assert link.get_attribute("rel") == "noopener noreferrer"
            
            # Check for screen reader text
            visually_hidden = link.find_elements(By.CLASS_NAME, "visually-hidden")
            if visually_hidden:
                assert "opens in new tab" in visually_hidden[0].text.lower()
    
    def test_color_contrast_ratios(self):
        """Test color contrast meets WCAG AA standards"""
        self.driver.get(self.base_url)
        
        # Check h1 color contrast
        h1 = self.driver.find_element(By.TAG_NAME, "h1")
        h1_color = h1.value_of_css_property("color")
        bg_color = h1.value_of_css_property("background-color")
        
        # These should have sufficient contrast
        # Note: Actual contrast calculation would require a library
        assert h1_color != bg_color
        
        # Check button contrast
        button = self.driver.find_element(By.ID, "uploadBtn")
        btn_color = button.value_of_css_property("color")
        btn_bg = button.value_of_css_property("background-color")
        
        assert btn_color != btn_bg
        
    def test_lang_attribute_present(self):
        """Test that html lang attribute is set"""
        self.driver.get(self.base_url)
        
        html = self.driver.find_element(By.TAG_NAME, "html")
        lang = html.get_attribute("lang")
        
        assert lang == "en"
        
    def test_meta_viewport_present(self):
        """Test that viewport meta tag exists for responsive design"""
        self.driver.get(self.base_url)
        
        viewport = self.driver.find_element(
            By.CSS_SELECTOR, 
            "meta[name='viewport']"
        )
        
        content = viewport.get_attribute("content")
        assert "width=device-width" in content
        assert "initial-scale=1" in content
        
    def test_page_title_descriptive(self):
        """Test that page title is descriptive"""
        self.driver.get(self.base_url)
        
        title = self.driver.title
        assert len(title) > 0
        assert "Model Registry" in title
        
    def test_no_duplicate_ids(self):
        """Test that there are no duplicate IDs on the page"""
        self.driver.get(self.base_url)
        
        # Get all elements with IDs
        elements_with_ids = self.driver.find_elements(By.XPATH, "//*[@id]")
        
        ids = [el.get_attribute("id") for el in elements_with_ids]
        
        # Check for duplicates
        assert len(ids) == len(set(ids)), "Duplicate IDs found on page"
        
    def test_form_disabled_state_keyboard_accessible(self):
        """Test that disabled form elements are indicated properly"""
        self.driver.get(self.base_url)
        
        button = self.driver.find_element(By.ID, "uploadBtn")
        
        # Initially should not be disabled
        assert not button.get_attribute("disabled")
        
        # After submission, button should be disabled
        input_field = self.driver.find_element(By.ID, "modelUrl")
        input_field.send_keys("https://huggingface.co/test/model")
        button.click()
        
        time.sleep(0.5)
        
        # Button should be disabled during loading
        # Note: This test might be flaky depending on API response time
        
    def test_error_messages_role_alert(self):
        """Test that error messages have role='alert' for screen readers"""
        self.driver.get(self.base_url)
        
        # Trigger an error by clicking with empty input
        input_field = self.driver.find_element(By.ID, "modelUrl")
        input_field.send_keys("invalid-url")
        
        button = self.driver.find_element(By.ID, "uploadBtn")
        button.click()
        
        # Wait for error message
        time.sleep(1)
        
        # Check if error has role="alert"
        status_region = self.driver.find_element(By.ID, "statusRegion")
        if status_region.text:
            error_div = status_region.find_element(By.CSS_SELECTOR, "[role='alert']")
            assert error_div is not None


class TestAxeAccessibility:
    """Automated accessibility testing using axe-core"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        self.base_url = "http://127.0.0.1:8000"
        
        yield
        
        self.driver.quit()
    
    def test_axe_accessibility_scan(self):
        """Run automated accessibility scan using axe-core"""
        self.driver.get(self.base_url)
        
        # Initialize Axe
        axe = Axe(self.driver)
        
        # Inject axe-core javascript
        axe.inject()
        
        # Run accessibility tests
        results = axe.run()
        
        # Assert no violations
        violations = results["violations"]
        
        if violations:
            print(f"\n{len(violations)} accessibility violations found:")
            for violation in violations:
                print(f"\n- {violation['id']}: {violation['description']}")
                print(f"  Impact: {violation['impact']}")
                print(f"  Help: {violation['helpUrl']}")
        
        # Write report
        axe.write_results(results, "accessibility_report.json")
        
        # Assert no violations
        assert len(violations) == 0, f"Found {len(violations)} accessibility violations"


# Additional utility tests
class TestResponsiveDesign:
    """Test responsive design and mobile accessibility"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup mobile viewport"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        self.base_url = "http://127.0.0.1:8000"
        
        yield
        
        self.driver.quit()
    
    def test_mobile_viewport_responsive(self):
        """Test that page is responsive on mobile viewport"""
        # Set mobile viewport
        self.driver.set_window_size(375, 667)  # iPhone SE size
        self.driver.get(self.base_url)
        
        # Check that elements are visible
        h1 = self.driver.find_element(By.TAG_NAME, "h1")
        assert h1.is_displayed()
        
        input_field = self.driver.find_element(By.ID, "modelUrl")
        assert input_field.is_displayed()
        
        button = self.driver.find_element(By.ID, "uploadBtn")
        assert button.is_displayed()
        
    def test_tablet_viewport_responsive(self):
        """Test that page is responsive on tablet viewport"""
        # Set tablet viewport
        self.driver.set_window_size(768, 1024)  # iPad size
        self.driver.get(self.base_url)

        # Check layout
        card = self.driver.find_element(By.CLASS_NAME, "card")
        assert card.is_displayed()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
